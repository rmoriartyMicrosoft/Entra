import requests
from azure.identity import ClientSecretCredential

# === Placeholder values for secure use ===
tenant_id = "YOUR_TENANT_ID"
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
workspace_id = "YOUR_WORKSPACE_ID"

# Authenticate using app registration
credential = ClientSecretCredential(tenant_id, client_id, client_secret)

# Log Analytics KQL query
query = """
AuditLogs
| where OperationName == "Invite external user"
| extend inviteTime = TimeGenerated-90d
| extend daysSinceInvite = datetime_diff("day", now(), inviteTime)
| where daysSinceInvite == 90
| extend upn = tostring(TargetResources[0].id)
| project upn, inviteTime, daysSinceInvite
"""
timespan = "P90D"

# Query Log Analytics
def run_log_analytics_query(workspace_id, query, timespan):
    token = credential.get_token("https://api.loganalytics.io/.default")
    headers = {
        'Authorization': f'Bearer {token.token}',
        'Content-Type': 'application/json'
    }

    url = f"https://api.loganalytics.io/v1/workspaces/{workspace_id}/query"
    body = {
        'query': query,
        'timespan': timespan
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()

# Delete user from Microsoft Graph
def delete_user(user_id):
    graph_token = credential.get_token("https://graph.microsoft.com/.default")
    graph_headers = {
        'Authorization': f'Bearer {graph_token.token}',
        'Content-Type': 'application/json'
    }

    delete_url = f"https://graph.microsoft.com/v1.0/users/{user_id}"

    response = requests.delete(delete_url, headers=graph_headers)
    if response.status_code == 204:
        print(f"✅ Successfully deleted user {user_id}")
    else:
        print(f"❌ Failed to delete user {user_id}: {response.status_code} {response.text}")

# Run
try:
    result = run_log_analytics_query(workspace_id, query, timespan)
    columns = [col["name"] for col in result["tables"][0]["columns"]]
    rows = result["tables"][0]["rows"]

    print("=== Users Invited Exactly 90 Days Ago ===")
    for row in rows:
        record = dict(zip(columns, row))
        user_id = record['upn']
        print(f"User: {user_id}, Invited: {record['inviteTime']}")
        delete_user(user_id)