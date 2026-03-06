# Contributing to SpecGen AI

Thanks for your interest in contributing! This project is in early alpha and feedback from QA engineers is especially valuable.

## Ways to Contribute

### Report Bugs
Open an [issue](https://github.com/0xAshraFF/specgen-ai/issues) with:
- What you did (video type, length, app being recorded)
- What you expected
- What happened instead
- Screenshots of the output if relevant

### Suggest Features
Open an issue with the `enhancement` label. I'm especially interested in:
- New test framework support (Selenium, Cypress, etc.)
- Output format improvements
- Prompt engineering improvements for better test generation

### Submit Code
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test locally with a screen recording
5. Submit a PR with a clear description

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/specgen-ai.git
cd specgen-ai
pip install -r requirements.txt
python main.py
```

## Code Style
- Python: Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Keep the prompt engineering in `services/ai_client.py` well-documented

## Questions?
Open a discussion or reach out via issues. No question is too basic.
