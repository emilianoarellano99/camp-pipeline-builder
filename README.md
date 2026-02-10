# CAMP Pipeline Builder MCP

An MCP (Model Context Protocol) server that helps you build CAMP pipelines conversationally through Claude Code.

## What This Does

Instead of spending hours manually configuring CAMP pipelines, you can now:
- Describe what you want to extract in natural language
- Preview the pipeline structure with visual diagrams
- Walk through each step conversationally
- Get smart suggestions for models and normalization patterns
- Generate complete, ready-to-use CAMP configurations

**Example:** "I want to extract alcohol content from wine products"
→ Complete pipeline with input, extraction, normalization, and publish steps in minutes.

## Features

📋 **Visual Pipeline Preview**
- ASCII diagrams showing pipeline structure
- Interactive approval before configuration

🤖 **Smart Assistance**
- Suggests best LLM models based on CAMP usage stats
- Auto-generates regex patterns for normalization
- Explains operation modes (batch vs sync)

🔧 **Step-by-Step Guidance**
- Asks questions one at a time
- Fills in sensible defaults
- Keeps JSON configs clean and hidden until final assembly

## Installation

### Quick Install (Recommended)

**Prerequisites:** Claude Code CLI installed

Run this one-liner in your terminal:

```bash
curl -sSL https://raw.githubusercontent.com/emilianoarellano99/camp-pipeline-builder/main/install.sh | bash
```

This will:
- Install to `~/.camp-mcp-server`
- Set up Python environment
- Register with Claude Code
- Verify installation

Then restart Claude Code and you're ready!

---

### Manual Installation

If you prefer to install manually:

**Prerequisites:**
- Python 3.8+
- Claude Code CLI installed

**Steps:**

1. Clone this repository:
```bash
git clone https://github.com/emilianoarellano99/camp-pipeline-builder.git
cd camp-pipeline-builder
```

2. Create virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Register the MCP with Claude Code:
```bash
claude mcp add camp-pipeline-builder \
  --type stdio \
  --command "$(pwd)/venv/bin/python" \
  --arg "$(pwd)/server.py"
```

4. Restart Claude Code

## Usage

Start Claude Code and simply describe what you want to extract:

```
"I want to extract alcohol content from wine products"
```

The MCP will:
1. Show you a visual diagram of the pipeline structure
2. Ask for your approval
3. Walk you through configuring each step:
   - Input: Which table, ID column, how many records
   - Extract: Which model, what prompt, which fields
   - Normalize: What output format (auto-suggests regex patterns)
   - Publish: Which fields to write back
4. Generate the complete pipeline JSON ready for CAMP

## Available Commands

Once the MCP is active, you can ask:
- "Show me available CAMP models"
- "Explain batch vs sync modes"
- "List CAMP step types"

## Example Output

After walking through the steps, you'll get:
- ✅ Complete pipeline orchestration JSON
- ✅ Individual step configurations
- ✅ All with proper UUIDs and connections
- ✅ Ready to import into CAMP

## Architecture

- **server.py**: Main MCP server with 11 tools
- Uses real CAMP data (16 models, usage stats, operation modes)
- Generates clean JSON with conversational guidance
- Supports Input, Extract, Normalize, Audit, and Publish steps

## Tools Available

| Tool | Description |
|------|-------------|
| `preview` | Show pipeline structure diagram |
| `input` | Generate Snowflake input step |
| `extract` | Generate LLM extraction step |
| `suggest_patterns` | Smart regex pattern suggestions |
| `normalize` | Generate normalization step |
| `publish` | Generate publish step |
| `assemble` | Combine all steps into final pipeline |
| `models` | List available CAMP models |
| `explain_modes` | Explain operation modes |
| `step_types` | List CAMP step types |

## Contributing

This MCP is designed to reduce CAMP friction across Instacart. Contributions welcome:
- Add new step types (QAS, DataBridge)
- Improve pattern suggestions
- Add more helper tools
- Enhance diagram visualization

## License

Internal Instacart tool

## Contact

Built by Emiliano Arellano
Feedback and iterations welcome!
