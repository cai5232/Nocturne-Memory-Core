# Nearfield — optional recent-life context

Nearfield keeps a small, decaying map of recent days beside durable memory.
It is meant for fragments that matter now but should not all become permanent
memories: recent projects, jokes, unresolved practical details, changes in tone,
and relationship context.

The pipeline is deliberately separate from Breath and permanent buckets:

```text
chat JSONL
  -> one compact first-person diary per day
  -> recent days assembled with decreasing character quotas
  -> Nearfield.md injected once per session on UserPromptSubmit
```

Nearfield is **not** a complete transcript or proof of lived experience. Treat it
as a recent map; consult chat history when exact wording or attribution matters.

## Privacy

Nearfield is disabled until you run it. It sends sampled chat text to the model
endpoint you configure. Use a local OpenAI-compatible endpoint if the ledger
must not leave your machine. Generated files can contain intimate information;
keep `nearfield/`, chat ledgers, names, and API keys out of public repositories.

## Configure

Required:

```bash
export NOCTURNE_CHAT_LEDGER=/path/to/chat_history.jsonl
export NOCTURNE_NEARFIELD_API_KEY=...
export NOCTURNE_NEARFIELD_MODEL=gpt-4o-mini
```

Optional:

```bash
export NOCTURNE_NEARFIELD_BASE_URL=http://localhost:1234/v1
export NOCTURNE_NEARFIELD_DIR=/path/to/private/nearfield
export NOCTURNE_NEARFIELD_TZ=Asia/Shanghai
export NOCTURNE_AGENT_NAME=Nox
export NOCTURNE_HUMAN_NAME=Jia
```

The ledger reader accepts JSONL rows with `ts`/`timestamp`/`created_at`, `role`,
and `text` or `content` fields.

## Generate

Generate yesterday and assemble the latest seven days:

```bash
python nearfield.py
```

Backfill or only rebuild the rolling file:

```bash
python nearfield.py --date 2026-08-10
python nearfield.py --assemble-only
```

Schedule `python nearfield.py` once a day with cron, Task Scheduler, launchd, or
your existing job runner. It writes:

```text
nearfield/days/YYYY-MM-DD.md
nearfield/Nearfield.md
```

## Inject on UserPromptSubmit

The example hook is Claude Code-compatible:

```bash
cp hooks/example.settings.json /path/to/your/hook-settings.json
```

Edit its absolute paths, then set the reader path when needed:

```bash
export NOCTURNE_NEARFIELD_PATH=/path/to/private/nearfield/Nearfield.md
```

The hook injects at most once per session (36-hour sticky by default) and caps
the payload at 1,800 characters. It does not regenerate or call a model during
prompt submission.
