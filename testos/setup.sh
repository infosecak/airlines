#!/bin/bash
set -e

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from template - edit it now and add your OpenAI API key."
fi

echo ""
echo "Setup complete. Next time, run:"
echo "  source venv/bin/activate"
echo "  streamlit run app.py"
