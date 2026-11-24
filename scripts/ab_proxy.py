from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen

class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        variant = "B" if self.headers.get("X-Experiment", "").upper() == "B" else "A"
        target = f"http://aceest-{variant.lower()}-service:5000{self.path}"

        try:
            request = Request(target, headers={"X-Forwarded-For": self.client_address[0]})
            with urlopen(request, timeout=5) as response:
                body = response.read()
                status = response.status

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Experiment-Variant", variant)
            self.end_headers()
            self.wfile.write(body)
        except Exception as error:
            self.send_error(502, str(error))

HTTPServer(("0.0.0.0", 8080), Proxy).serve_forever()
