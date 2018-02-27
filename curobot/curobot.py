import argparse
import json
import logging
import time
from threading import Thread

from steem import Steem
from steem.post import Post
from steembase.exceptions import PostDoesNotExist

from threading import Semaphore

logger = logging.getLogger('curobot')
logger.setLevel(logging.INFO)
logging.basicConfig()


class TransactionListener:

    def __init__(self, steem, config):
        self.steem = steem
        self.account = config["account"]
        self.rules = config["rules"]
        self.authors = set([r["author"] for r in self.rules])
        self.mutex = Semaphore()

    @property
    def properties(self):
        props = self.steem.get_dynamic_global_properties()
        if not props:
            logger.info('Couldnt get block num. Retrying.')
            return self.properties
        return props

    def get_author_rule(self, author):
        for rule in self.rules:
            if rule["author"] == author:
                return rule

    @property
    def last_block_num(self):
        return self.properties['head_block_number']

    @property
    def block_interval(self):
        config = self.steem.get_config()
        return config["STEEMIT_BLOCK_INTERVAL"]

    def run(self):
        last_block = self.last_block_num
        while True:
            while (self.last_block_num - last_block) > 0:
                last_block += 1
                self.check_block(last_block)

            # Sleep for one block
            block_interval = self.block_interval
            logger.info('Sleeping for %s seconds.', block_interval)
            time.sleep(block_interval)

    def upvote(self, post, retry_count=0, sleep_time=0):

        if sleep_time > 0:
            logger.info("Vote-sleep for %s seconds.", sleep_time)
            time.sleep(sleep_time)

        rule = self.get_author_rule(post["author"])

        # skip it if we already voted on that.
        for vote in post.get("active_votes"):
            if vote["voter"] == self.account:
                logger.info("Already upvoted: %s", post.identifier)
                return

        # does the post have a bad tag?
        bad_tags = rule.get("bad_tags", [])
        if len(set(bad_tags).intersection(set(post.get("tags", [])))) > 0:
            logger.info("Post has a bad tag. Skipping. %s", post.identifier)
            return

        self.mutex.acquire()
        logger.info("Vote mutex acquired.")

        elapsed_minutes = int(post.time_elapsed().seconds / 60)
        if elapsed_minutes >= rule["vote_delay"]:
            try:
                post.commit.vote(
                    post.identifier,
                    rule["weight"],
                    account=self.account)
                self.mutex.release()
                logger.info("Vote mutex released.")
            except Exception as error:
                logger.error(error)
                if retry_count < 3:
                    self.mutex.release()
                    logger.info("Vote mutex released.")
                    return self.upvote(post, retry_count=retry_count + 1)
                else:
                    logger.info(
                        "Tried 3 times but failed. %s", post.identifier)
                    self.mutex.release()
                    logger.info("Vote mutex released.")
                    return
        else:
            remaining_time_for_upvote = (rule["vote_delay"] - elapsed_minutes)\
                                        * 60
            thread = Thread(
                target=self.upvote,
                args=(post,),
                kwargs={"sleep_time": remaining_time_for_upvote})
            thread.start()
            self.mutex.release()
            logger.info("Vote mutex released.")

    def check_block(self, block_num):
        logger.info("Parsing block: %s", block_num)
        operation_data = self.steem.get_ops_in_block(
            block_num, virtual_only=False)

        for operation in operation_data:
            operation_type, raw_data = operation["op"][0:2]
            if operation_type == "comment":
                try:
                    post = Post(raw_data)
                except PostDoesNotExist:
                    continue

                if not post.is_main_post():
                    # we're only interested in posts.
                    continue

                if post["author"] in self.authors:
                    thread = Thread(
                        target=self.upvote, args=(post,))
                    thread.start()


def listen(config):
    logger.info('Starting Curobot TX listener...')
    steem = Steem(nodes=config.get("nodes"), keys=config["keys"])
    tx_listener = TransactionListener(steem, config)
    tx_listener.run()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Config file in JSON format")
    args = parser.parse_args()
    config = json.loads(open(args.config).read())
    return listen(config)


if __name__ == '__main__':
    main()
