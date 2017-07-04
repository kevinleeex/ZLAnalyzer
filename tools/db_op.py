import pymongo

word='课程顾问'
client = pymongo.MongoClient('localhost')
db = client['zhilian']
table = db['机器学习']
table.remove({'zwmc': {'$regex': word}})
