import argparse
import json
import logging
import time
from datetime import datetime
from os import makedirs
from os.path import expanduser, exists
from threading import Thread

import dataset
from steem import Steem
from steem.post import Post
from steembase.exceptions import RPCError, PostDoesNotExist

logger = logging.getLogger('curobot')
logger.setLevel(logging.INFO)
logging.basicConfig()

CONFIG_PATH = expanduser('~/.curobot')
STATE = expanduser("%s/state" % CONFIG_PATH)
CHECKPOINT = expanduser("%s/checkpoint" % CONFIG_PATH)


def load_state(fallback_data=None):
    try:
        return json.loads(open(STATE).read())
    except FileNotFoundError as e:
        if not exists(CONFIG_PATH):
            makedirs(CONFIG_PATH)

        dump_state(fallback_data)
        return load_state()


def dump_state(data):
    f = open(STATE, 'w+')
    f.write(json.dumps(data))
    f.close()


def load_checkpoint(fallback_block_num=None):
    try:
        return int(open(CHECKPOINT).read())
    except FileNotFoundError as e:
        if not exists(CONFIG_PATH):
            makedirs(CONFIG_PATH)

        dump_checkpoint(fallback_block_num)
        return load_checkpoint()


def dump_checkpoint(block_num):
    f = open(CHECKPOINT, 'w+')
    f.write(str(block_num))
    f.close()


class TransactionListener(object):

    def __init__(self, steem, config):
        self.steem = steem
        self.account = config["account"]
        self.rules = config["rules"]
        self.authors = set([r["author"] for r in self.rules])
        self.mysql_uri = config["mysql_uri"]

    def get_table(self, table):
        db = dataset.connect(self.mysql_uri)
        return db[table]

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

    def process_block(self, block_num, retry_count=0):
        block_data = self.steem.get_block(block_num)

        if not block_data:
            if retry_count > 3:
                logger.error(
                    'Retried 3 times to get this block: %s Skipping.',
                    block_num
                )
                return

            logger.error(
                'Couldnt read the block: %s. Retrying.', block_num)
            self.process_block(block_num, retry_count=retry_count + 1)

        logger.info('Processing block: %s', block_num)
        if 'transactions' not in block_data:
            return

        self.check_block(block_num)
        dump_state(self.properties)

    def run(self, start_from=None):
        if start_from is None:
            last_block = load_checkpoint(
                fallback_block_num=self.last_block_num,
            )
            logger.info('Last processed block: %s', last_block)
        else:
            last_block = start_from
        while True:

            while (self.last_block_num - last_block) > 0:
                last_block += 1
                self.process_block(last_block)
                dump_checkpoint(last_block)

            # Sleep for one block
            block_interval = self.block_interval
            logger.info('Sleeping for %s seconds.', block_interval)
            time.sleep(block_interval)

    def upvote(self, post, retry_count=0):

        full_link = "@%s/%s" % ( post["author"], post["permlink"])

        if retry_count > 3:
            logger.info(
                "Tried to upvote this 3 times. %s No luck. Skipping.",
                full_link)

        already_upvoted = self.get_table('upvote').find_one(
                author=post["author"], permlink=post["permlink"]
        )
        if already_upvoted:
            logger.info('Already voted. Skipping. %s', full_link)
            return

        rule = self.get_author_rule(post["author"])
        elapsed_minutes = int(post.time_elapsed().seconds / 60)
        if elapsed_minutes >= rule["vote_delay"]:
            try:
                resp = post.commit.vote(post.identifier, rule["weight"],
                                        account=self.account)
                if not resp:
                    retry_count += 1
                    return self.upvote(retry_count=retry_count)

                logger.info("Upvoted %s.", full_link)
                self.get_table('upvote').insert(dict(
                    author=post["author"],
                    permlink=post["permlink"],
                    created_at=str(datetime.now()),
                ))
            except RPCError as e:
                if 'You have already voted' in e.args[0]:
                    logger.info('Already voted. Skipping. %s', full_link)

                raise
            except Exception as e:
                logger.error("Failed upvoting: %s", full_link)
                raise
        else:
            remaining_time_for_upvote = (rule["vote_delay"] - elapsed_minutes)\
                                        * 60
            logger.info(
                "Sleeping %s seconds to upvote @%s/%s.",
                remaining_time_for_upvote,
                post["author"],
                post["permlink"]
            )
            time.sleep(60)
            post.refresh()
            return self.upvote(post, retry_count=0)

    def check_block(self, block_num):
        operation_data = self.steem.get_ops_in_block(
            block_num, virtual_only=False)

        for operation in operation_data:
            operation_type, raw_data = operation["op"][0:2]
            if operation_type == "comment":
                try:
                    post = Post(raw_data)
                except PostDoesNotExist:
                    continue
                if post.is_comment():
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
