import dony


# for detect-secrets python pre-commit hook
def update_secrets_baseline():
    dony.shell("""
        set -euo pipefail
        uv tool install detect-secrets
        uvx detect-secrets scan > .secrets.baseline
    """)

