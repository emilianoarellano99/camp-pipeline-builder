#!/bin/bash
set -e

echo "🚀 CAMP Pipeline Builder - Automated Installation"
echo "=================================================="
echo ""

# Check if Claude Code CLI is installed
if ! command -v claude &> /dev/null; then
    echo "❌ Error: Claude Code CLI is not installed"
    echo "Please install Claude Code first: https://claude.ai/download"
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

INSTALL_DIR="$HOME/.camp-mcp-server"

echo "📁 Installation directory: $INSTALL_DIR"
echo ""

# Remove existing installation if present
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Existing installation found. Removing..."
    rm -rf "$INSTALL_DIR"
fi

# Clone repository
echo "📦 Cloning repository..."
git clone https://github.com/emilianoarellano99/camp-pipeline-builder.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment and install dependencies
echo "📚 Installing dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Register with Claude Code
echo "🔗 Registering with Claude Code..."
claude mcp remove camp-pipeline-builder 2>/dev/null || true  # Remove if exists
claude mcp add camp-pipeline-builder \
  --type stdio \
  --command "$INSTALL_DIR/venv/bin/python" \
  --arg "$INSTALL_DIR/server.py"

# Verify installation
echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Verification:"
claude mcp list | grep camp-pipeline-builder || echo "⚠️  MCP registered but not connected yet"

echo ""
echo "🎯 Next Steps:"
echo "1. Restart Claude Code (if already running)"
echo "2. Start a new session: claude"
echo "3. Try it out: \"I want to extract alcohol content from wine products\""
echo ""
echo "📖 Documentation: https://github.com/emilianoarellano99/camp-pipeline-builder"
echo ""
