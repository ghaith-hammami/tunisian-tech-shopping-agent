# Contributing

Follow the setup instructions in [README.md](README.md), then run the existing
offline tests before submitting a change:

```bash
python -m unittest discover -s tests -v
```

The tests use Python's built-in `unittest` framework, but require the application
dependencies to be installed. They do not need a Gemini API key or network access.
GitHub Actions runs the same command on pushes and pull requests.

## Reporting a problem

Include the Python version, the command you ran, the error message, and enough
details to reproduce the issue. For scraper problems, include the store and public
listing URL. Remove API keys and other private information from logs and screenshots.

## Making a change

- Keep changes focused and explain the resulting behavior in the pull request.
- For behavior changes, add or update relevant offline tests. Mock Gemini and HTTP
  requests rather than depending on live services.
- Store URLs and HTML selectors live in `shopping_agent/tools/stores.py`.
- Update the README and `.env.example` when adding configuration options.
- Keep credentials in your local `.env`; commit only placeholder configuration.

If you manually check live stores, describe that separately from the offline test
results. A passing unit test suite does not confirm that store selectors still work.
