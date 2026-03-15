# API Client Documentation

The project includes a lightweight API client:

```
zai_client.py
```

This file can be used independently in other Python projects.

## Example Usage

```python
from zai_client import ZaiClient

client = ZaiClient("your_api_token")

quota = client.get_quota()

print(quota.level)
print(quota.time_limit.remaining)
print(quota.time_limit.percentage)
print(quota.time_limit.next_reset_datetime)

for detail in quota.time_limit.usage_details:
    print(detail.model_code, detail.usage)

if quota.error:
    print("Error:", quota.error)
```

## Dependencies

The client only requires:

```
requests
```
