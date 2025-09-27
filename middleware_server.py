import json
import datetime
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("middleware-demo")

# ----------------------------
# Step 1: Define Middleware
# ----------------------------
def log_middleware(next_handler):
    async def handler(request):
        # Mask sensitive data if present
        masked_request = request.copy()
        if "password" in masked_request.get("params", {}):
            masked_request["params"]["password"] = "***MASKED***"

        # Log incoming request
        print(f"[{datetime.datetime.now()}] Request: {json.dumps(masked_request)}")

        # Call the next handler
        response = await next_handler(request)

        # Mask sensitive info in response if needed
        masked_response = response.copy()
        if "secret" in masked_response.get("result", {}):
            masked_response["result"]["secret"] = "***MASKED***"

        # Log outgoing response
        print(f"[{datetime.datetime.now()}] Response: {json.dumps(masked_response)}")

        return response

    return handler

# Register the middleware
mcp.use(log_middleware)

# ----------------------------
# Step 2: Define a Sample Tool
# ----------------------------
@mcp.tool()
async def echo_secret(message: str, password: str):
    """Echoes a message but also handles a sensitive password parameter."""
    return {
        "message": message,
        "password": password,   # Will be masked in the logs
        "secret": "TOP_SECRET_VALUE"
    }

# ----------------------------
# Step 3: Run the Server
# ----------------------------
if __name__ == "__main__":
    mcp.run()
