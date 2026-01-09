import re
from functools import partial
import asyncio
import dony


async def has_local_changes(shell):
    try:
        await shell(
            "git diff-index --quiet HEAD --",
            quiet=True,
        )
        return False
    except Exception:
        return True


@dony.command()
async def split_merge(path: str):
    """Helper for merging the current branch into main without a PR:
    - allows splitting changes into multiple commits,
    - unnecessary changes can be stashed,
    - result — clean history in main.
    """

    # - Set up shell with run_from

    shell = partial(
        dony.shell,
        run_from=dony.find_repo_root(path),
    )

    # - Check that github email is properly set

    email = (await shell("git config --global user.email", quiet=True)).strip()

    if not email:
        return await dony.error("Global git user.email is NOT set.")

    if not re.match(r"^\d+\+[^@]+@users\.noreply\.github\.com$", email):
        return await dony.error(
            """
            Email does not match github noreply format
            Go to https://github.com/settings/emails to get it and set it with git config --global user.email "123456+username@users.noreply.github.com" command
            """,
        )

    # - Get target branch

    target_branch = await dony.input(
        "Target branch:",
        default=await shell(
            "git branch --list main | grep -q main && echo main || echo master",
            quiet=True,
        ),
    )

    # - Check if target branch exists

    if await shell(f"git branch --list {target_branch}") == "":
        return await dony.error(f"Target branch {target_branch} does not exist")

    # - Get current branch

    merged_branch = await shell(
        "git branch --show-current",
        quiet=True,
    )

    # - Merge with target branch first

    if await has_local_changes(shell):
        return await dony.error("You have local changes. Please commit them first.")

    await shell(
        f"""

        # - Push current branch

        git push

        # - Merge with target branch

        git checkout {target_branch}
        git pull
        """,
        quiet=True,
    )

    # - Checkout to target branch

    await shell(f"git checkout {target_branch}")

    # - Apply restore from merged branch UNSTAGED

    await shell(f"git restore --source={merged_branch} --worktree .")

    # - Wait for the user to do commits

    while True:
        await dony.press_any_key("Press any key when you are done with commits...")

        if not await has_local_changes(shell):
            break

        await dony.echo("You have local changes")
        if await dony.confirm("Stash and proceed?"):
            await shell("git stash --include-untracked")
            break

    # - When done - remove original branch and push main

    await shell(
        f"""
        git branch -D {merged_branch}
        git push origin --delete {merged_branch}
        git push
        """,
    )


if __name__ == "__main__":
    asyncio.run(split_merge(path=__file__))