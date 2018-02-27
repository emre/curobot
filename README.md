# curobot
Your personal curation bot on the steem network™
### Installation

```bash
(sudo) pip install curobot
```

You're all set. (You need python 3.6+)

### Running


```bash
$ POSTING_KEY=private_wif curobot config_file.json
```

### Configuration Details

```javascript
{
  "rules": [
    {"author": "foo", "weight": 50.0, "vote_delay": 30},
    {"author": "bar", "weight": 50.0, "vote_delay": 30},
  ],
  "keys": ["PRIVATE_KEY"],
  "account": "emrebeyler",
  "mysql_uri": "mysql+pymysql://root:pass@localhost/curobot",
  "nodes": ["https://rpc.buildteam.io"]
}
```

**rules**

| author        | weight             | vote_delay          | bad_tags   |
| ------------- |--------------------|---------------------|---------------------
| account username | vote power in percentage | X minutes before vote | list of blacklisted tag |


**account**

Voter account name

**nodes**

RPC nodes to connect. Default is api.steemit.com

