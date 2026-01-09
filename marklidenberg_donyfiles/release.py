import os
import asyncio
from functools import partial
from typing import Optional

import dony
from dotenv import load_dotenv


@dony.command()
async def release(
    path: str,
    version: Optional[str] = None,
    uv_publish_token: Optional[str] = None,
):
    """Bump version and publish to PyPI"""

    # - Set up shell with run_from

    shell = partial(
        dony.shell,
        run_from=dony.find_repo_root(path),
    )

    # - Load .env

    load_dotenv()

    # - Get main branch

    main_branch = await shell(
        "git branch --list main | grep -q main && echo main || echo master",
        quiet=True,
    )

    # - Select default arguments

    version = version or await dony.select(
        "Choose version",
        choices=[
            "patch",
            "minor",
            "major",
        ],
    )

    uv_publish_token = uv_publish_token or await dony.input(
        "Enter UV publish token (usually a PyPI token)",
        default=os.getenv("UV_PUBLISH_TOKEN", ""),
    )

    # - Get current branch

    original_branch = await shell(
        "git branch --show-current",
        quiet=True,
    )

    # - Go to main

    await shell(f"""

        # - Exit if there are staged changes

        git diff --cached --name-only | grep -q . && git stash

        # - Go to main

        git checkout {main_branch}

        # - Git pull

        git pull
    """)

    # - Bump

    await shell(
        f"""

        # - Bump

        VERSION=$(uv version --bump {version} --short)
        echo $VERSION

        # - Commit, tag and push

        git add pyproject.toml
        git commit --message "chore: release-$VERSION"
        git tag --annotate "release-$VERSION" --message "chore: release-$VERSION" HEAD
        git push
        git push origin "release-$VERSION" # push tag to origin,
        """
    )

    # - Build and publish

    await shell(
        f"""
        rm -rf dist/* # remove old builds
        uv build
        UV_PUBLISH_TOKEN={uv_publish_token} uv publish
        """
    )

    # - Go back to original branch

    await shell(
        f"""
        git checkout {original_branch}
        git merge --no-edit {main_branch} && git push
        """
    )

if __name__ == "__main__":
    asyncio.run(release(path=__file__))