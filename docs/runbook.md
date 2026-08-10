# Как повторить BPI Challenge 2012 run

Перед загрузкой прочитайте актуальные [условия 4TU](https://doi.org/10.4121/resource:terms_of_use).
Скрипт скачивает только публичный XES-файл версии 1, проверяет опубликованный
MD5 и сохраняет raw data вне репозитория.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
PYTHONPATH=src .venv/bin/python scripts/fetch_bpi2012.py \
  --data-dir /tmp/process-mining-bpi2012
PYTHONPATH=src .venv/bin/python scripts/run_bpi2012.py \
  --dataset /tmp/process-mining-bpi2012/BPI_Challenge_2012.xes.gz \
  --fetch-manifest /tmp/process-mining-bpi2012/fetch-manifest.json \
  --output-dir studies/bpi-challenge-2012-2026-08-10
PYTHONPATH=src .venv/bin/python scripts/render_bpi2012_charts.py \
  studies/bpi-challenge-2012-2026-08-10/results.json \
  --output-dir studies/bpi-challenge-2012-2026-08-10/graphs
```

Повторный запуск может отличаться только окружением и временем, если источник
переиздан. До сравнения результатов сверяйте version, calculated SHA-256,
source manifest, commit кода и параметры из `results.json`.

Локальные проверки:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
ruff check src tests scripts
PYTHONPATH=src .venv/bin/python -m compileall -q src scripts
```
