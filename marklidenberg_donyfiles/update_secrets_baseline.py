from functools import partial
import asyncio
import dony


@dony.command()
async def update_secrets_baseline(path: str):
    """For detect-secrets python pre-commit hook"""

    shell = partial(
        dony.shell,
        run_from=dony.find_repo_root(path),
    )

    await shell("""
        set -euo pipefail
        uv tool install detect-secrets
        uvx detect-secrets scan > .secrets.baseline
    """)


if __name__ == "__main__":
    asyncio.run(update_secrets_baseline(path=__file__))