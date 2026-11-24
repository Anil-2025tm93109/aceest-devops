from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from scripts.ab_proxy import Proxy


def make_handler(variant=None):
    handler = object.__new__(Proxy)
    handler.headers = {"X-Experiment": variant} if variant else {}
    handler.path = "/health"
    handler.client_address = ("127.0.0.1", 12345)
    handler.wfile = BytesIO()

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.send_error = MagicMock()

    return handler


@pytest.mark.parametrize(
    ("header", "expected_variant"),
    [
        ("A", "A"),
        ("B", "B"),
        (None, "A"),
    ],
)
def test_proxy_routes_experiment_variants(header, expected_variant):
    handler = make_handler(header)

    response = MagicMock()
    response.status = 200
    response.read.return_value = b'{"status":"healthy"}'

    context = MagicMock()
    context.__enter__.return_value = response

    with patch("scripts.ab_proxy.Request") as mock_request, \
         patch("scripts.ab_proxy.urlopen", return_value=context) as mock_urlopen:
        handler.do_GET()

    mock_request.assert_called_once()
    assert mock_request.call_args.args[0] == (
        f"http://aceest-{expected_variant.lower()}-service:5000/health"
    )
    mock_urlopen.assert_called_once_with(mock_request.return_value, timeout=5)

    handler.send_response.assert_called_once_with(200)
    handler.send_header.assert_any_call("Content-Type", "application/json")
    handler.send_header.assert_any_call(
        "X-Experiment-Variant", expected_variant
    )
    assert handler.wfile.getvalue() == b'{"status":"healthy"}'


def test_proxy_returns_502_when_backend_fails():
    handler = make_handler("A")

    with patch(
        "scripts.ab_proxy.urlopen",
        side_effect=OSError("Backend unavailable"),
    ):
        handler.do_GET()

    handler.send_error.assert_called_once_with(
        502, "Backend unavailable"
    )
