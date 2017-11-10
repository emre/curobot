# curobot
Your personal curation bot on the steem network™
### Installation

```bash
(sudo) pip install curobot
```

You're all set. (You need python 3.6+)

### Running


```bash
$ curobot config_file.json
```

### Configuration Details

```javascript
{
  "rules": [
    {"author": "keepcalmanddread", "weight": 50.0, "vote_delay": 30},
    {"author": "fetch", "weight": 50.0, "vote_delay": 30},
  ],
  "keys": ["PRIVATE_KEY"],
  "account": "emrebeyler",
  "mysql_uri": "mysql+pymysql://root:pass@localhost/curobot",
  "nodes": ["https://rpc.buildteam.io"]
}
```

**rules**

| author        | weight             | vote_delay          |    
| ------------- |--------------------|---------------------|     
| account username | vote power in percentage | X minutes before vote |

**keys**

Your private posting key

**account**

Voter account name

**mysql_uri** 

mySQL connection string

**nodes**

RPC nodes to connect. Default is rpc.buildteam.io.

