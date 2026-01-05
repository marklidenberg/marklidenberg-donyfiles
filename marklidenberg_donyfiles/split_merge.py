import re

import dony

def has_local_changes():
    try:
        dony.shell(
            "git diff-index --quiet HEAD --",
            quiet=True,
        )
        return False
    except Exception:
        return True


@dony.command(run_from="git_root")
def split_merge():
    """Helper for merging the current branch into main without a PR:
    - allows splitting changes into multiple commits,
    - unnecessary changes can be stashed,
    - result — clean history in main.
    """

    # - Check that github email is properly set

    email = dony.shell("git config --global user.email", quiet=True).strip()

    if not email:
        return dony.error("Global git user.email is NOT set.")

    if not re.match(r"^\d+\+[^@]+@users\.noreply\.github\.com$", email):
        return dony.error(
            """
            Email does not match github noreply format
            Go to https://github.com/settings/emails to get it and set it with git config --global user.email "123456+username@users.noreply.github.com" command
            """,
        )

    # - Get target branch

    target_branch = dony.input(
        "Target branch:",
        default=dony.shell(
            "git branch --list main | grep -q main && echo main || echo master",
            quiet=True,
        ),
    )

    # - Check if target branch exists

    if dony.shell(f"git branch --list {target_branch}") == "":
        return dony.error(f"Target branch {target_branch} does not exist")

    # - Get current branch

    merged_branch = dony.shell(
        "git branch --show-current",
        quiet=True,
    )

    # - Merge with target branch first

    if has_local_changes():
        return dony.error("You have local changes. Please commit them first.")

    dony.shell(
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

    dony.shell(f"git checkout {target_branch}")

    # - Apply restore from merged branch UNSTAGED

    dony.shell(f"git restore --source={merged_branch} --worktree .")

    # - Wait for the user to do commits

    while True:
        dony.press_any_key("Press any key when you are done with commits...")

        if not has_local_changes():
            break

        dony.echo("You have local changes")
        if dony.confirm("Stash and proceed?"):
            dony.shell("git stash --include-untracked")
            break

    # - When done - remove original branch and push main

    dony.shell(
        f"""
        git branch -D {merged_branch}
        git push origin --delete {merged_branch}
        git push
        """,
    )


if __name__ == "__main__":
    split_merge()
