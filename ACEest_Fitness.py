"""
Backward-compatible entry point for the ACEest Fitness application.

The canonical Flask implementation remains in app.py.
This module re-exports the application rather than duplicating code.
"""

from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
