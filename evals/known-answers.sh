#!/bin/sh
# Known-answer checks for the skills that judge by meaning, against real commits
# in github.com/mattyv/skope. These call Jev (through jev-semgrep), so they cost a
# little and aren't in CI. Run them after changing a risk's wording or a recipe.
#   evals/known-answers.sh        needs skope, jev-semgrep's semgrep and a key
set -u
here=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git clone -q https://github.com/mattyv/skope.git "$work/skope"
cd "$work/skope" || exit 1
fails=0

check() { # name, got, want
  if [ "$2" = "$3" ]; then echo "PASS  $1"; else echo "FAIL  $1: got '$2', want '$3'"; fails=$((fails + 1)); fi
}

# review-focus: where each commit's review should go.
for case in "71ece54 No code changes" "0d6e941 Careful review" "b4b2089 Careful review"; do
  commit=${case%% *}; want=${case#* }
  git -c advice.detachedHead=false checkout -q "$commit"
  got=$(SKOPE_CALLER=agent skope "$here/skills/review-focus/SKILL.md" --dry-run --param "base=$(git rev-parse --short "$commit^")" 2>/dev/null \
    | sed -n 's/.*"event":"transfer".*"to":"\([^"]*\)".*/\1/p' | tail -n 1)
  check "review-focus $commit" "$got" "$want"
done
git checkout -q main

# when-did-this-change: the right commit is among the recipe's hits (newer noise may come first).
fmt='%x00%h %ad %s%n%b'
while IFS='|' read -r want question; do
  got=$(git log -p --no-merges -150 --date=short --format="$fmt" | semgrep -z -e "$question" \
    | tr '\0' '\n' | grep -E '^[0-9a-f]{7,} [0-9]{4}-' | grep -o "^$want" | head -n 1)
  check "when-did-this-change: $question" "$got" "$want"
done <<'CASES'
c14865a|starts accepting an unquoted number as a fake command result
05457e6|stops treating a zombie process group as still running
58712ae|fixes a Docker image build that failed because a file was missing
CASES

[ "$fails" -eq 0 ] && echo "all known answers match" || { echo "$fails mismatched"; exit 1; }
