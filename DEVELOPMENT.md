# Development Guide: Building the CAMP Pipeline Builder MCP

This document explains how this MCP was created, for anyone wanting to understand the process or build similar tools.

## What is an MCP?

**Model Context Protocol (MCP)** is a standard way to extend Claude's capabilities with custom tools. Unlike skills (which are predefined commands), MCPs are:
- Server processes that Claude Code connects to
- Provide multiple tools/functions Claude can call
- Can maintain state and perform complex operations
- Work automatically when conversation topics match their capabilities

**Note:** While this is technically an MCP server, in practice it functions similarly to a Claude Code skill - providing specialized tools for CAMP pipeline generation.

## The Problem We're Solving

### Current CAMP Pipeline Creation Process

Creating a CAMP pipeline today involves:
- Navigating CAMP's UI to configure each step
- Understanding:
  - Step types (SnowflakeQueryInput, LLMPromptTemplate, Regex, etc.)
  - Available LLM models and their characteristics
  - Operation modes (batch vs sync)
  - Field mappings and data structures
- Multiple iterations to get configurations right
- No way to visualize the full pipeline before building it

**Key Pain Point:** There's a gap between understanding WHAT you want to extract (domain expertise) and HOW to configure CAMP to do it (technical implementation).

### The Vision (from Joe's Problem Solver RFD)

Joe Rustad's "Problem Solver" RFD identified critical pain points in CAMP:

**Workflow Rigidity:**
> "Ops teams must manually model every resolution flow as static DAGs... This leads to:
> - Duplicated effort across similar problems
> - Inconsistent handling of edge cases
> - Slow response to new product types or situations"

**Success Metrics from the RFD:**
- **Workflow creation time:** 80% reduction in time from need identified to workflow running
- **Ops workflow modeling:** 50% reduction in manual workflows created per quarter

### What This POC Tackles

This MCP addresses the Problem Solver vision by:

1. **Visual-First Approach:** Users see the pipeline structure as a diagram BEFORE diving into configuration
2. **Conversational Configuration:** Walk through each step with natural language instead of technical forms
3. **Domain Expert Accessibility:** Ops users can build pipelines without deep CAMP technical knowledge
4. **Rapid Iteration:** From idea to working pipeline in minutes instead of hours

**The Key Innovation:** Bridging the gap between "I want to extract alcohol content" (domain knowledge) and the technical CAMP configuration needed to do it.

While Joe's RFD proposes a Problem Solver that generates workflows dynamically at runtime based on input analysis, this POC demonstrates the same principle applied to the creation process itself - using AI to translate intent into implementation.

## Design Decisions

### 1. Conversational First

**Decision:** Users describe what they want in natural language, then walk through configuration step-by-step.

**Rationale:**
- Domain experts know WHAT they want but not HOW to configure CAMP
- Asking one question at a time reduces cognitive load
- Users can iterate on structure (diagram) before diving into details

**Alternative Considered:** Form-based UI
- Rejected because it still requires understanding all CAMP concepts upfront

### 2. Visual Pipeline Preview

**Decision:** Show ASCII diagram of pipeline structure before any configuration.

**Rationale:**
- Aligns with Problem Solver's principle: understand the goal before implementation details
- Users can approve/modify the pipeline flow before investing time in configuration
- Visual representation is easier to understand than technical descriptions

**Implementation Evolution:**
- Tried Mermaid (didn't render in terminal)
- Tried Graphviz PNG (required saving files, not immediate)
- Settled on ASCII box diagrams (immediate, clear, terminal-native)

### 3. Real Data, Not Assumptions

**Decision:** Query CAMP's production database for models, usage stats, step types, and operation modes.

**Current Implementation:**
- Queried `rds.catalog_camp` tables manually via Snowflake
- Hardcoded results into the MCP as Python dictionaries
- 16 models with usage statistics
- 6 step types
- Operation mode patterns

**Future Enhancement:**
With a Snowflake connector integrated into the MCP, we could:
- Query live for the latest available models in CAMP
- Detect new step types automatically as they're added
- Pull real-time usage statistics
- Adapt to structural changes in CAMP without code updates

**Trade-off for POC:**
- Static data = simpler authentication, faster responses
- Dynamic queries = always current, but adds complexity

### 4. Granular Tools, Not Monolithic

**Decision:** 11 separate tools instead of one "generate_pipeline" function.

**The 11 Tools:**

**Pipeline Building:**
1. `preview` - Show diagram and get structure approval
2. `input` - Generate SnowflakeQueryInput step
3. `extract` - Generate LLMPromptTemplate step
4. `suggest_patterns` - AI-powered regex pattern suggestions
5. `normalize` - Generate Regex normalization step
6. `publish` - Generate PublishToSnowflake step
7. `assemble` - Combine all steps into complete pipeline with UUIDs

**Helpers (on-demand):**
8. `models` - List available CAMP models with usage stats
9. `explain_modes` - Explain batch vs sync operation modes
10. `step_types` - List all CAMP step types
11. `hello_camp` - Connection test and capabilities overview

**Rationale:**
- Claude orchestrates the conversation, MCP handles generation
- Cleaner separation: conversation logic vs. config generation
- Each tool has a single, clear responsibility
- Easier to test and maintain

### 5. Hide JSON Until the End

**Decision:** Users only see confirmations during configuration, complete JSON at the end.

**Rationale:**
- Overwhelming to show JSON after every step
- Users care about "is this configured correctly?" not "what does the JSON look like?"
- JSON is returned in `<step_config>` tags for Claude to extract internally

**User Experience:**
```
✓ Input step configured
✓ Extraction step configured
✓ Normalization step configured
✓ Publish step configured
[Final assembled pipeline JSON]
```

### 6. MCP vs. Skill

**Decision:** Built as an MCP server, not a Claude Code skill.

**Rationale:**
- MCPs provide multiple tools (we need 11)
- MCPs can maintain state across tool calls
- MCPs are more flexible for complex interactions
- Can evolve into dynamic features later (live CAMP data queries, etc.)

**Note:** In practice, this functions similarly to a skill from the user's perspective - it's invoked conversationally when the topic matches.

### 7. Smart Defaults with Override Capability

**Decision:** Every parameter has a sensible default, but users can customize.

**Current Defaults (Hardcoded in POC):**

**Input Step:**
- Table: `catalog.external_interfaces.current_flattened_ml_products_view`
- ID column: `PRODUCT_ID`
- Limit: `1000` records
- Deduplication: Enabled on ID column

**Extraction Step:**
- Model: `gpt-5-mini` (unless user requests another)
- Test mode: `sync` (immediate execution for testing)
- Production mode: `batch` (queued processing for production)
- Properties: Currently requires manual specification by user

**Rationale:**
- Reduces decisions for new users
- Experts can override when needed
- Defaults based on CAMP usage statistics (batch/sync pattern appears in 59% of pipelines)

**Known Limitations (POC):**

These are hardcoded but should be dynamic:
- **Query table:** Currently defaults to products table, should detect based on use case
- **Query limit:** Fixed at 1000, should be configurable per user needs
- **Properties for extraction:** Requires user to specify which fields (product_name, images, etc.)
  - Future: Could auto-suggest based on input step fields
  - Future: Could pull from the input step's SELECT statement automatically
- **Model selection:** Defaults to gpt-5-mini unless user requests
  - Future: Could suggest based on attribute complexity

**Expected Evolution:**

This is a POC demonstrating feasibility. Production version would need:
- Dynamic property detection from input steps
- Table/limit recommendations based on attribute type
- Model recommendations based on complexity analysis
- Live data from Snowflake connector
- More flexible defaults per team/use case

## Technical Implementation

### Technology Stack

**Language:** Python 3.8+

**Framework:** Standard MCP SDK (`mcp` package)
- Tried FastMCP initially - had connection issues with Claude Code CLI
- Standard MCP SDK proved more stable and reliable

**Key Libraries:**
- `json` - Configuration generation and serialization
- `uuid` - Generate unique pipeline step IDs
- `mcp.server` - MCP server framework
- `mcp.types` - Tool and content type definitions

**Why These Choices:**
- Python: Common at Instacart for tooling and scripts, easy to integrate with MCP SDK
- **The OUTPUT is JSON** - CAMP pipelines are JSON configurations
- **The MCP itself is Python** - just the code that generates those JSON configs
- Standard MCP SDK: Stable, well-documented, works reliably with Claude Code
- Minimal dependencies: Easier to maintain and deploy

### Data Collection

Real CAMP data was extracted via Snowflake queries:

**Available Models Query:**
```sql
SELECT
    STEP_ATTRIBUTES:model::varchar as model_name,
    COUNT(*) as usage_count
FROM rds.catalog_camp.attribute_platform_step_versions sv
JOIN rds.catalog_camp.attribute_platform_steps s
    ON sv.step_id = s.id
WHERE s.step_type = 'LLMPromptTemplate'
    AND sv.is_latest = true
GROUP BY model_name
ORDER BY usage_count DESC;
```

**Operation Modes Query:**
```sql
SELECT
    COALESCE(STEP_ATTRIBUTES:productionOperationModel::varchar, 'null') as prod_mode,
    COALESCE(STEP_ATTRIBUTES:testOperationModel::varchar, 'null') as test_mode,
    COUNT(*) as usage_count
FROM rds.catalog_camp.attribute_platform_step_versions
WHERE step_id IN (
    SELECT id FROM rds.catalog_camp.attribute_platform_steps
    WHERE step_type = 'LLMPromptTemplate'
)
GROUP BY prod_mode, test_mode
ORDER BY usage_count DESC;
```

**Step Types Query:**
```sql
SELECT DISTINCT step_type, step_category
FROM rds.catalog_camp.attribute_platform_steps
WHERE tombstoned = false
ORDER BY step_category, step_type;
```

**Results Hardcoded Into MCP:**

```python
AVAILABLE_MODELS = {
    "gpt-4o": {"usage": 38, "description": "Most popular - General purpose"},
    "gpt-5": {"usage": 19, "description": "Advanced model"},
    "gpt-5-mini": {"usage": 12, "description": "Fast, cost-effective"},
    # ... 13 more models
}

OPERATION_MODES = {
    "sync": "Synchronous - immediate execution",
    "batch": "Batch - queued processing",
    "null": "Uses pipeline default"
}

STEP_TYPES = {
    "SnowflakeQueryInput": "INPUT - Query Snowflake",
    "LLMPromptTemplate": "EXTRACTION_MODEL - LLM extraction",
    "Regex": "NORMALIZATION - Regex transforms",
    "PublishToSnowflake": "PUBLISH - Write to catalog",
    "QAS": "AUDIT - Quality assurance",
    "DataBridge": "API_SERVICE - External APIs"
}
```

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Claude Code CLI                     │
│                                                         │
│  User: "Extract alcohol content from wine"             │
│                                                         │
│  Claude orchestrates conversational flow               │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol (stdio)
                     │
┌────────────────────▼────────────────────────────────────┐
│              CAMP Pipeline Builder MCP                  │
│                    (server.py)                          │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Tool Registry (11 tools)                        │  │
│  │  - preview, input, extract, normalize, publish   │  │
│  │  - suggest_patterns, assemble                    │  │
│  │  - models, explain_modes, step_types             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Generation Functions                            │  │
│  │  - generate_pipeline_diagram()                   │  │
│  │  - generate_input_step()                         │  │
│  │  - generate_extraction_step()                    │  │
│  │  - generate_normalization_patterns()             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CAMP Data (Hardcoded)                           │  │
│  │  - 16 models with usage stats                    │  │
│  │  - 6 step types                                   │  │
│  │  - Operation mode patterns                       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### How It Works

**1. Initialization:**
```bash
# Claude Code reads ~/.claude.json
# Launches: /path/to/venv/bin/python /path/to/server.py
# MCP server starts, registers 11 tools
# Claude Code establishes stdio connection
```

**2. User Request:**
```
User: "I want to extract alcohol content from wine products"
```

**3. Claude's Orchestration:**
```python
# Claude decides to use preview tool
preview(
    description="Extract alcohol content from wine",
    attribute_name="alcohol_content",
    include_normalize=True
)
```

**4. MCP Processes:**
```python
# Generate ASCII diagram
diagram = generate_pipeline_diagram(
    attribute_name="alcohol_content",
    include_normalize=True,
    include_audit=False
)

# Return to Claude
return f"""
{diagram}

Does this structure work?
"""
```

**5. User Approves → Claude Continues:**
```python
# Claude calls input tool
input(
    attribute_name="alcohol_content",
    table="default",
    limit=1000
)

# Returns clean confirmation + hidden JSON:
"""
✓ Input step configured

<step_config>
{
  "query": "SELECT...",
  "limit": 1000,
  ...
}
</step_config>
"""
```

**6. Claude Extracts JSON Internally:**
- Parses `<step_config>` tags
- Stores configuration
- Shows user only: "✓ Input step configured"
- Continues to next step

**7. Final Assembly:**
```python
# After all steps configured
assemble(
    name="Alcohol Content Pipeline",
    steps=[input_config, extract_config, ...]
)

# Generates UUIDs, connects steps, returns complete JSON
```

### Key Implementation Details

**Tool Response Format:**
```python
output = f"""✓ {step_type} step configured

User-friendly confirmation message here.

<step_config>
{json.dumps(config, indent=2)}
</step_config>
"""
```

Claude sees everything, extracts JSON from tags, shows user only the confirmation.

**Pipeline Assembly:**
```python
# Generate UUIDs for each step
pipeline_steps = []
for idx, step in enumerate(steps):
    step_id = str(uuid.uuid4())

    # Connect with nextStepsRule
    if idx < len(steps) - 1:
        next_step_id = str(uuid.uuid4())
        step["nextStepsRule"] = {
            "type": "singleNextStep",
            "nextStep": next_step_id
        }

    pipeline_steps.append(step)

# Final structure
{
    "firstPipelineStepId": first_step_uuid,
    "enableSchedule": False,
    "hoursInterval": 24,
    "steps": pipeline_steps
}
```

**Smart Pattern Suggestions:**

```python
if attribute_type == "percentage":
    return [
        {"match": r"(\d+\.?\d*)%", "replace": r"$1"},
        {"match": r"(\d+\.?\d*)\s*percent", "replace": r"$1"}
    ]
elif attribute_type == "boolean":
    return [
        {"match": "^yes$", "replace": "True"},
        {"match": "^no$", "replace": "False"},
        ...
    ]
```

Pattern suggestions are based on common data quality issues observed in CAMP workflows.

## Key Iterations & Learnings

This MCP was built iteratively using Claude Code itself - a meta experience of using AI to build AI tools.

### Major Iterations

**Connection & Framework:**
- Started with FastMCP (simpler API) → wouldn't connect to Claude Code CLI
- Switched to standard MCP SDK → stable connection
- Learning: Standard SDK more reliable for Claude Code

**Visual Diagrams:**
- Tried Mermaid → collapsed in terminal, not rendered
- Tried Graphviz → required saving/opening PNG files
- Settled on ASCII box diagrams → immediate, terminal-native

**Tool Architecture:**
- Started monolithic (one `generate_pipeline` tool)
- Split into 11 granular tools (input, extract, normalize, etc.)
- Learning: Let Claude orchestrate, MCP just provides tools

**User Experience:**
- Initially showed full JSON after each step → overwhelming
- Wrapped JSON in `<step_config>` tags → Claude extracts, users see confirmations
- Shortened tool names (`generate_input_step` → `input`) → cleaner UI

**Smart Features:**
- Added helper tools (models, explain_modes, step_types)
- Built `suggest_patterns` for AI-powered regex generation
- Integrated real CAMP data from Snowflake queries

### Key Learnings

**Technical:**
- Standard MCP SDK > FastMCP for Claude Code CLI
- ASCII diagrams work best for terminal tools
- Granular tools > monolithic functions
- Hide complexity, show confirmations only

**UX:**
- Visual preview BEFORE configuration is critical
- One question at a time reduces cognitive load
- Real data > assumptions for suggestions
- Users want to see WHAT they're building, not HOW

**Process:**
- Iterate quickly with real user feedback (Joe, Matt demos)
- Each iteration addressed a specific pain point
- Meta-experience: using Claude Code to build Claude Code tools
- POCs demonstrate feasibility, not production readiness

### What's Next

This is a POC. Future iterations will depend on:
- Team feedback and adoption
- Integration requirements (Snowflake connector, dynamic data)
- Expanding to other CAMP use cases beyond pipeline creation
- Potential evolution toward Joe's full Problem Solver vision

## Usage & Examples

### Basic Usage

Once the MCP is installed and Claude Code is running:

**1. Start a conversation:**
```
"I want to extract alcohol content from wine products"
```

**2. Review the diagram:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAMP PIPELINE STRUCTURE                          │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐        ┌──────────────────┐
  │   📥 INPUT       │  ───▶  │  🤖 EXTRACT      │
  │                  │        │                  │
  │ Snowflake Query  │        │  LLM Extraction  │
  └──────────────────┘        └──────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │ 🔧 NORMALIZE     │
                              │                  │
                              │  Regex Patterns  │
                              └──────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  📤 PUBLISH      │
                              │                  │
                              │ Snowflake Catalog│
                              └──────────────────┘

Does this pipeline structure work for you?
```

**3. Approve and configure:**
```
User: "Yes"
→ Claude walks through each step
→ Asks for table, model, normalization format, etc.
→ Generates configs one by one
```

**4. Get final pipeline:**
```json
{
  "firstPipelineStepId": "uuid-here",
  "enableSchedule": false,
  "steps": [...]
}
```

### Example Scenarios

**Scenario 1: Simple Extraction (No Normalization)**

```
User: "Extract brand names from products"

→ Preview shows: Input → Extract → Publish
→ User: "Yes"
→ Claude: "What model should we use?"
→ User: "gpt-4o"
→ Result: 3-step pipeline ready to import
```

**Scenario 2: With Normalization**

```
User: "Extract alcohol percentages from beverages"

→ Preview shows: Input → Extract → Normalize → Publish
→ User: "Yes"
→ Claude: [configures input step]
→ Claude: "What format for output?"
→ User: "Just the number, like 12.5"
→ Claude: [suggests regex patterns to remove %, ABV, etc.]
→ Result: 4-step pipeline with smart normalization
```

**Scenario 3: Using Helper Tools**

```
User: "What models are available in CAMP?"

→ Claude calls 'models' tool
→ Shows: gpt-4o (38 usage), gpt-5 (19 usage), etc.

User: "Now extract nutrition facts with gpt-4o"
→ Claude uses that model for extraction step
```

**Scenario 4: Understanding Operation Modes**

```
User: "What's the difference between batch and sync?"

→ Claude calls 'explain_modes' tool
→ Explains: sync = immediate, batch = queued
→ Shows usage stats: 59 pipelines use null/null (default)
```

### Output Structure

The MCP generates two types of outputs:

**Individual Step Configs:**
```json
{
  "query": "SELECT PRODUCT_ID AS entity_id, 'alcohol_content' AS entity_type, * FROM ...",
  "limit": 1000,
  "useDeduplication": true,
  "deduplicationFields": ["PRODUCT_ID"]
}
```

**Complete Pipeline Orchestration:**
```json
{
  "firstPipelineStepId": "7f90bc7a-05d3-417e-91ba-377792e19044",
  "enableSchedule": false,
  "hoursInterval": 24,
  "cronError": null,
  "steps": [
    {
      "pipelineStepId": "uuid-1",
      "stepId": "1",
      "stepVersionId": "1001",
      "version": "1",
      "type": "task",
      "attributeOverrides": {},
      "nextStepsRule": {
        "type": "singleNextStep",
        "nextStep": "uuid-2"
      }
    },
    ...
  ]
}
```

### Tips for Best Results

**Be Specific About Intent:**
- ❌ "Extract data"
- ✅ "Extract alcohol content from wine products"

**Review the Diagram First:**
- Approve structure before diving into details
- Request changes early: "Add normalization step"

**Let Defaults Work:**
- Most defaults are based on CAMP usage patterns
- Override only when you have specific needs

**Use Helpers When Needed:**
- "What models are available?"
- "Explain batch vs sync"
- "Show me step types"

**Iterate Conversationally:**
- "Change the model to gpt-4o"
- "Increase limit to 10,000"
- "Use sync mode for production"

## Known Limitations & Getting Help

### Current Limitations (POC)

**1. Hardcoded Data**
- Models, step types, operation modes are static
- Data accurate as of February 2025
- New CAMP features won't appear automatically

**2. Limited Property Configuration**
- Extraction step properties require manual specification
- No auto-detection from input step fields
- Can't suggest which fields are needed for specific attributes

**3. Fixed Defaults**
- Table always defaults to `current_flattened_ml_products_view`
- Limit fixed at 1000
- No intelligence about appropriate defaults per use case

**4. Basic Step Coverage**
- Supports: Input, Extract, Normalize, Publish
- Missing: QAS (Audit), DataBridge (API calls)
- No support for branching pipelines

**5. Single Pipeline Flow**
- Only linear pipelines (A → B → C → D)
- No conditional branching
- No parallel steps

**6. Manual Import Required**
- Generates JSON, user must import into CAMP UI
- No direct CAMP API integration

### Getting Help

**Issues or Questions:**
- Open an issue on GitHub: https://github.com/emilianoarellano99/camp-pipeline-builder
- Reach out to Emiliano Arellano

---

**Built by:** Emiliano Arellano
**Inspired by:** Joe Rustad's "Problem Solver" RFD
**Purpose:** Proof-of-concept demonstrating AI-assisted CAMP pipeline creation
