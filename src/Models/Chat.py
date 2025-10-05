from pymodm import MongoModel, fields


# 👥 Group Model
class Chat(MongoModel):
    chat_id = (fields.CharField(required=True),)
    xp = fields.IntegerField(required=True, min_value=0, default=0)
    captcha = fields.BooleanField(default=False, required=True)
    events = fields.BooleanField(default=False, required=True)
    mod = fields.BooleanField(default=False, required=True)
