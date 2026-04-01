"""
Config lives here.  Everything reads from env vars so we can
swap values between local dev and Render without touching code.
"""

import os

HOSPITAL_API_BASE = os.getenv(
    "HOSPITAL_API_BASE",
    "https://hospital-directory.onrender.com",
)

# hard cap from the spec
MAX_CSV_ROWS = 20

# how many concurrent requests we fire at the upstream API
# keep it modest so we don't overwhelm a free-tier Render box
CONCURRENCY_LIMIT = 5
