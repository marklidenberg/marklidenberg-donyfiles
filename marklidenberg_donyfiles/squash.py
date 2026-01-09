import re
from functools import partial
import asyncio
import dony


@dony.command()
async def squash(path: str):
    """Squashes current branch into target branch"""

    # - Set up shell with run_from

    shell = partial(
        dony.shell,
        run_from=dony.find_repo_root(path),
    )

    # - Get target branch

    default_branch = await shell(
        "git branch --list main | grep -q main && echo main || echo master",
        quiet=True,
    )
    target_branch = await dony.input(
        "Enter target branch:",
        default=default_branch or "",
    )

    # - Get current branch

    merged_branch = await shell(
        "git branch --show-current",
        quiet=True,
    )

    # - Merge with target branch first

    await shell(
        f"""

        # push if there are unpushed commits
        git diff --name-only | grep -q . && git push

        git fetch origin
        git checkout {target_branch}
        git pull
        git checkout {merged_branch}

        git merge {target_branch}

        if ! git diff-index --quiet HEAD --; then

          # try to commit twice, in case of formatting errors that are fixed by the first commit
          git commit -m "Merge with target branch" || git commit -m "Merge with target branch"
          git push
        else
          echo "Nothing merged – no commit made."
        fi
        """,
    )

    # - Do git diff

    await shell(
        f"""
        root=$(git rev-parse --show-toplevel)

        git diff {target_branch} --name-only -z \
        | while IFS= read -r -d '' file; do
            full="$root/$file"
            printf '\033[1;35m%s\033[0m\n' "$full"
            git --no-pager diff --color=always {target_branch} -- "$file" \
              | sed $'s/^/\t/'
            printf '\n'
          done
"""
    )

    # - Ask user to confirm

    if not await dony.confirm("Start squashing?"):
        return

    # - Check if target branch exists

    if (
        await shell(
            f"""
        git branch --list {target_branch}
    """
        )
        == ""
    ):
        return await dony.error(f"Target branch {target_branch} does not exist")

    # - Get commit message from the user

    while True:
        commit_message = await dony.input(
            f"Enter commit message for merging branch {merged_branch} to {target_branch}:"
        )
        if bool(
            re.match(
                r"^(?:(?:feat|fix|docs|style|refactor|perf|test|chore|build|ci|revert)(?:\([A-Za-z0-9_-]+\))?(!)?:)\s.+$",
                commit_message.splitlines()[0],
            )
        ):
            break
        await dony.echo("Only conventional commits are allowed, try again")

    # - Check if user wants to remove merged branch

    remove_merged_branch = await dony.confirm(
        f"Remove merged branch {merged_branch}?",
    )

    # - Do the process

    await shell(
        f"""

        # - Make up to date

        git diff --name-only | grep -q . && git stash push -m "squash-{merged_branch}"
        git checkout {target_branch}

        # - Set upstream if needed

        if ! git ls-remote --heads --exit-code origin "{target_branch}" >/dev/null; then
            git push --set-upstream origin {target_branch} --force
        fi

        # - Pull target branch

        git pull

        # - Merge

        git merge --squash {merged_branch}

        # try to commit twice, in case of formatting errors that are fixed by the first commit
        git commit -m "{commit_message}" || git commit -m "{commit_message}"
        git push

        # - Remove merged branch

        if {str(remove_merged_branch).lower()}; then
            git branch -D {merged_branch}
            git push origin --delete {merged_branch}
        fi
    """,
    )


if __name__ == "__main__":
    asyncio.run(squash(path=__file__))