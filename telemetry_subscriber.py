import json
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()

# Endpoint for live telemetry SSE stream
TELEMETRY_STREAM_URL = "http://127.0.0.1:5005/telemetry/stream"

def listen_to_telemetry():
    console.print(Panel("[bold cyan]LATRIVEX ATF L11 Telemetry Subscriber Started Listening...[/bold cyan]"))
    
    try:
        response = requests.get(TELEMETRY_STREAM_URL, stream=True)
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    data = json.loads(decoded_line[5:])
                    
                    layer = data.get("layer", "UNKNOWN")
                    status = data.get("status", "INFO")
                    details = data.get("details", {})

                    console.print(
                        f"[bold yellow][{layer} Telemetry][/bold yellow] "
                        f"Status: [bold green]{status}[/bold green] | "
                        f"Payload: {details}"
                    )
    except Exception as e:
        console.print(f"[bold red]Telemetry Stream Disconnected:[/bold red] {e}")

if __name__ == "__main__":
    listen_to_telemetry()