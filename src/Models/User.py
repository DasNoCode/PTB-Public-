from pymodm import MongoModel, fields
from zoneinfo import ZoneInfo
from datetime import datetime

# default timezone
INDIA_TZ = ZoneInfo("Asia/Kolkata")


# 👤 User Model
class User(MongoModel):
    user_id = fields.CharField(required=True)
    xp = fields.IntegerField(required=True, min_value=0, default=0)
    ban = fields.BooleanField(required=True, default=False)
    reason = fields.CharField(default="None")
    banned_at = fields.DateTimeField()
    created_at = fields.DateTimeField(
        default=datetime.now(INDIA_TZ), required=True
    )
