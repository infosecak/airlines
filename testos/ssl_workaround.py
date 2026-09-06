"""
Optional, explicit workaround for corporate-proxy SSL interception, for use
ONLY when the proper fix (installing your corporate root CA - see README)
isn't practical right now. This trades away protection against
man-in-the-middle attacks, so it's opt-in via DISABLE_SSL_VERIFY=true in
.env, and should only be used on a network you already trust (your own
company's proxy on your own company's laptop) - never on public wifi.

Unlike pip-system-certs/truststore, this does NOT monkeypatch
ssl.SSLContext's own methods (which is what caused the RecursionError on
macOS) - it only changes the default `verify` argument that httpx/httpx2
clients are constructed with, which is a much lighter touch.
"""

import os
import warnings


def maybe_disable_ssl_verification():
    if os.getenv("DISABLE_SSL_VERIFY", "").strip().lower() != "true":
        return

    warnings.warn(
        "DISABLE_SSL_VERIFY=true - SSL certificate verification is OFF for "
        "outbound API calls. Only use this on a network you trust.",
        stacklevel=2,
    )

    # Patch both possible module names - different openai/langsmith SDK
    # versions have used either the standard `httpx`/`httpcore` packages or
    # renamed `httpx2`/`httpcore2` forks internally.
    for module_name in ("httpx", "httpx2"):
        try:
            module = __import__(module_name)
        except ImportError:
            continue

        for client_attr in ("Client", "AsyncClient"):
            client_cls = getattr(module, client_attr, None)
            if client_cls is None:
                continue

            original_init = client_cls.__init__

            def make_patched(original):
                def patched(self, *args, **kwargs):
                    # Force this, don't setdefault - callers like the
                    # openai SDK pass verify= explicitly (often a
                    # truststore.SSLContext), so setdefault would never
                    # actually override it.
                    kwargs["verify"] = False
                    original(self, *args, **kwargs)

                return patched

            client_cls.__init__ = make_patched(original_init)
