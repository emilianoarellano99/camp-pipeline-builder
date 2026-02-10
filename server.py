#!/usr/bin/env python3
"""
CAMP Pipeline Builder MCP Server
Generates complete CAMP pipeline configurations from natural language prompts
"""

import json
import uuid
from mcp.server import Server
from mcp.types import Tool, TextContent

# Create MCP server
server = Server("camp-pipeline-builder")

# Real CAMP configuration data (from Snowflake queries)
AVAILABLE_MODELS = {
    "gpt-4o": {"usage": 38, "description": "Most popular - General purpose, good quality"},
    "gpt-5": {"usage": 19, "description": "Advanced model, higher quality"},
    "gpt-5-mini": {"usage": 12, "description": "Faster, cost-effective"},
    "gpt-4.1": {"usage": 9, "description": "Stable version"},
    "o3": {"usage": 8, "description": "Reasoning model"},
    "gpt-4.1-2025-04-14": {"usage": 19, "description": "GPT-4.1 dated version"},
    "gpt-5-2025-08-07": {"usage": 7, "description": "GPT-5 dated version"},
    "gemini-2.0-flash-finetuned-ave-1.0": {"usage": 3, "description": "Fine-tuned Gemini"},
    "gpt-5.2": {"usage": 3, "description": "GPT-5.2 advanced"},
    "gpt-4.1-mini": {"usage": 2, "description": "Smaller GPT-4.1"},
    "gpt-4o-mini": {"usage": 2, "description": "Smaller GPT-4o"},
    "gemini-2.5-pro": {"usage": 2, "description": "Latest Gemini pro"},
    "gemini-2.0-flash-001": {"usage": 1, "description": "Gemini flash"},
    "o4-mini-2025-04-16": {"usage": 1, "description": "O4 mini"},
    "claude-sonnet-4": {"usage": 1, "description": "Anthropic Claude"},
    "gpt-5-nano": {"usage": 1, "description": "Smallest GPT-5"}
}

STEP_TYPES = {
    "SnowflakeQueryInput": "INPUT - Query Snowflake for product data",
    "LLMPromptTemplate": "EXTRACTION_MODEL - Use LLM to extract attributes",
    "Regex": "NORMALIZATION - Apply regex transformations",
    "PublishToSnowflake": "PUBLISH - Write results back to catalog",
    "QAS": "AUDIT - Quality assurance step",
    "DataBridge": "API_SERVICE - Call external APIs"
}

OPERATION_MODES = {
    "sync": "Synchronous execution - Processes immediately, good for testing",
    "batch": "Batch execution - Queues for later processing, cost-efficient for production",
    "null": "No mode specified - Uses pipeline-level default"
}

DEFAULT_TABLES = {
    "product": "catalog.external_interfaces.current_flattened_ml_products_view",
    "retailer": "catalog.catalog.retailer_view",
    "store": "catalog.catalog.store_view"
}

def generate_pipeline_diagram(attribute_name: str, include_normalize: bool, include_audit: bool) -> str:
    """Generate ASCII diagram for pipeline structure displayed in terminal"""

    # Build pipeline flow
    diagram = """
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAMP PIPELINE STRUCTURE                          │
└─────────────────────────────────────────────────────────────────────────┘

"""

    # Always start with Input → Extract
    diagram += """
  ┌──────────────────┐        ┌──────────────────┐
  │   📥 INPUT       │  ───▶  │  🤖 EXTRACT      │
  │                  │        │                  │
  │ Snowflake Query  │        │  LLM Extraction  │
  └──────────────────┘        └──────────────────┘
"""

    # Optional Normalize
    if include_normalize:
        diagram += """
                                        │
                                        ▼
                              ┌──────────────────┐
                              │ 🔧 NORMALIZE     │
                              │                  │
                              │  Regex Patterns  │
                              └──────────────────┘
"""

    # Optional Audit
    if include_audit:
        diagram += """
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  ✓ AUDIT         │
                              │                  │
                              │  Quality Check   │
                              └──────────────────┘
"""

    # Always end with Publish
    diagram += """
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  📤 PUBLISH      │
                              │                  │
                              │ Snowflake Catalog│
                              └──────────────────┘
"""

    return diagram

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="hello_camp",
            description="Test tool - returns a greeting",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="preview",
            description="Preview pipeline structure with diagram",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What you want to extract"
                    },
                    "attribute_name": {
                        "type": "string",
                        "description": "Name of the attribute"
                    },
                    "include_normalize": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include normalization step"
                    },
                    "include_audit": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include audit step"
                    }
                },
                "required": ["description", "attribute_name"]
            }
        ),
        Tool(
            name="input",
            description="Generate input step. Returns JSON in <step_config> tags - extract but don't show to user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attribute_name": {
                        "type": "string",
                        "description": "Attribute name (e.g., 'alcohol_content')"
                    },
                    "table": {
                        "type": "string",
                        "default": "catalog.external_interfaces.current_flattened_ml_products_view",
                        "description": "Source table to query"
                    },
                    "id_column": {
                        "type": "string",
                        "default": "PRODUCT_ID",
                        "description": "Unique identifier column (e.g., PRODUCT_ID, UPC, RETAILER_ID)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 1000,
                        "description": "Number of records to process"
                    },
                    "use_deduplication": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable deduplication"
                    }
                },
                "required": ["attribute_name"]
            }
        ),
        Tool(
            name="extract",
            description="Generate extraction step. Returns JSON in <step_config> tags - extract but don't show to user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attribute_name": {
                        "type": "string",
                        "description": "Attribute name"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Extraction prompt instructions"
                    },
                    "model": {
                        "type": "string",
                        "enum": list(AVAILABLE_MODELS.keys()),
                        "default": "gpt-5-mini",
                        "description": "LLM model to use"
                    },
                    "properties": {
                        "type": "array",
                        "description": "Fields the LLM needs access to (JSON array of {propertyName, images, required})",
                        "default": []
                    },
                    "production_mode": {
                        "type": "string",
                        "enum": ["sync", "batch", "null"],
                        "default": "batch",
                        "description": "Production operation mode"
                    },
                    "test_mode": {
                        "type": "string",
                        "enum": ["sync", "batch", "null"],
                        "default": "sync",
                        "description": "Test operation mode"
                    }
                },
                "required": ["attribute_name", "prompt"]
            }
        ),
        Tool(
            name="suggest_patterns",
            description="Suggest regex patterns for normalization",
            inputSchema={
                "type": "object",
                "properties": {
                    "attribute_type": {
                        "type": "string",
                        "description": "Type of attribute (e.g., 'percentage', 'boolean', 'number', 'text')"
                    },
                    "desired_output": {
                        "type": "string",
                        "description": "Desired output format or examples"
                    },
                    "common_errors": {
                        "type": "string",
                        "description": "Expected common errors or variations (optional)"
                    }
                },
                "required": ["attribute_type", "desired_output"]
            }
        ),
        Tool(
            name="normalize",
            description="Generate normalization step. Returns JSON in <step_config> tags - extract but don't show to user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attribute_name": {
                        "type": "string",
                        "description": "Attribute name"
                    },
                    "patterns": {
                        "type": "array",
                        "description": "Array of regex pattern objects with match/replace rules"
                    }
                },
                "required": ["attribute_name", "patterns"]
            }
        ),
        Tool(
            name="publish",
            description="Generate publish step. Returns JSON in <step_config> tags - extract but don't show to user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attribute_name": {
                        "type": "string",
                        "description": "Attribute name"
                    },
                    "mappings": {
                        "type": "array",
                        "description": "Field mappings: [{attributeName, campField, required}]",
                        "default": []
                    }
                },
                "required": ["attribute_name"]
            }
        ),
        Tool(
            name="assemble_pipeline",
            description="Assemble complete pipeline with all steps and orchestration",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Pipeline name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Pipeline description"
                    },
                    "steps": {
                        "type": "array",
                        "description": "Array of step configurations (from generate_*_step tools)"
                    }
                },
                "required": ["name", "steps"]
            }
        ),
        Tool(
            name="models",
            description="List available CAMP models",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="explain_modes",
            description="Explain batch vs sync modes",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["sync", "batch", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="step_types",
            description="List CAMP step types",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if name == "hello_camp":
        return [TextContent(
            type="text",
            text="""🚀 CAMP Pipeline Builder

Build CAMP pipelines conversationally. I can:

📋 Preview structure • Generate configs • Walk you step-by-step
🤖 Suggest models • Auto-generate regex patterns
🔧 List models • Explain modes • Show step types

Example: "Extract alcohol content from wine products"
"""
        )]

    elif name == "preview":
        attribute_name = arguments["attribute_name"]
        description = arguments["description"]
        include_normalize = arguments.get("include_normalize", False)
        include_audit = arguments.get("include_audit", False)

        # Generate ASCII diagram for terminal display
        diagram_ascii = generate_pipeline_diagram(attribute_name, include_normalize, include_audit)

        # Count steps
        step_count = 2  # Input + Extract
        if include_normalize:
            step_count += 1
        if include_audit:
            step_count += 1
        step_count += 1  # Publish

        output = f"""# Pipeline Preview: {attribute_name}

**Goal:** {description}
**Total Steps:** {step_count}

{diagram_ascii}

─────────────────────────────────────────────────────────────

**Does this pipeline structure work for you?**

Reply with:
• "Yes" - I'll build this pipeline step-by-step
• "Add normalization" - Include a regex normalization step
• "Add audit" - Include a quality assurance step
• Or describe what you'd like to change
"""

        return [TextContent(type="text", text=output)]

    elif name == "input":
        attribute_name = arguments["attribute_name"]
        table = arguments.get("table", "catalog.external_interfaces.current_flattened_ml_products_view")
        id_column = arguments.get("id_column", "PRODUCT_ID")
        limit = arguments.get("limit", 1000)
        use_deduplication = arguments.get("use_deduplication", True)

        # Generate clean query template
        query = f"""SELECT
    {id_column} AS entity_id,
    '{attribute_name}' AS entity_type,
    *
FROM {table}"""

        step_config = {
            "query": query,
            "limit": limit,
            "useDeduplication": use_deduplication,
            "deduplicationFields": [id_column] if use_deduplication else [],
            "rankingField": "",
            "useRanking": False
        }

        # Return JSON in hidden format for Claude to extract internally
        output = f"""✓ Input step configured

Querying {limit:,} records from `{table}` using `{id_column}` as identifier.

<step_config>
{json.dumps(step_config, indent=2)}
</step_config>
"""

        return [TextContent(type="text", text=output)]

    elif name == "extract":
        attribute_name = arguments["attribute_name"]
        prompt = arguments["prompt"]
        model = arguments.get("model", "gpt-5-mini")
        properties = arguments.get("properties", [])
        production_mode = arguments.get("production_mode", "batch")
        test_mode = arguments.get("test_mode", "sync")

        step_config = {
            "model": model,
            "prompt": prompt,
            "properties": properties,
            "costAttributionSourceId": "catalog-ops",
            "flattenOutput": True,
            "productionOperationModel": production_mode if production_mode != "null" else None,
            "testOperationModel": test_mode if test_mode != "null" else "sync",
            "outputPrefix": "",
            "usePrefix": False
        }

        # Return JSON in hidden format for Claude to extract internally
        output = f"""✓ Extraction step configured

Using **{model}** with {len(properties)} field(s) configured.

<step_config>
{json.dumps(step_config, indent=2)}
</step_config>
"""

        return [TextContent(type="text", text=output)]

    elif name == "suggest_patterns":
        attribute_type = arguments["attribute_type"]
        desired_output = arguments["desired_output"]
        common_errors = arguments.get("common_errors", "")

        # Smart pattern suggestions based on attribute type
        suggestions = []

        if attribute_type.lower() in ["boolean", "bool", "true/false"]:
            suggestions = [
                {"match": "^1$", "replace": "True", "description": "Convert 1 to True"},
                {"match": "^0$", "replace": "False", "description": "Convert 0 to False"},
                {"match": "(?i)^yes$", "replace": "True", "description": "Convert yes to True"},
                {"match": "(?i)^no$", "replace": "False", "description": "Convert no to False"},
                {"match": "(?i)^true$", "replace": "True", "description": "Standardize true"},
                {"match": "(?i)^false$", "replace": "False", "description": "Standardize false"},
                {"match": "(?i)^y$", "replace": "True", "description": "Convert y to True"},
                {"match": "(?i)^n$", "replace": "False", "description": "Convert n to False"}
            ]
        elif attribute_type.lower() in ["percentage", "percent", "%"]:
            suggestions = [
                {"match": r"(\d+\.?\d*)%", "replace": r"$1", "description": "Remove % sign, keep number"},
                {"match": r"^(\d+\.?\d*)\s*percent", "replace": r"$1", "description": "Remove 'percent' word"},
                {"match": r"^(\d+)$", "replace": r"$1.0", "description": "Ensure decimal format"}
            ]
        elif attribute_type.lower() in ["number", "numeric", "integer", "float"]:
            suggestions = [
                {"match": r"[,\s]", "replace": "", "description": "Remove commas/spaces from numbers"},
                {"match": r"^(\d+\.?\d*)[^\d]*$", "replace": r"$1", "description": "Extract just the number"},
                {"match": r"^(\d+)$", "replace": r"$1.0", "description": "Normalize to decimal"}
            ]
        else:
            suggestions = [
                {"match": r"^\s+|\s+$", "replace": "", "description": "Trim whitespace"},
                {"match": r"\s{2,}", "replace": " ", "description": "Collapse multiple spaces"}
            ]

        output = f"""# Suggested Normalization Patterns

**Attribute Type:** {attribute_type}
**Desired Output:** {desired_output}

## Recommended Patterns:

"""
        for i, pattern in enumerate(suggestions, 1):
            output += f"{i}. **{pattern['description']}**\n"
            output += f"   - Match: `{pattern['match']}`\n"
            output += f"   - Replace: `{pattern['replace']}`\n\n"

        output += """---

These patterns will handle common variations. You can:
- Use all suggested patterns
- Pick specific ones
- Add your own custom patterns
"""

        return [TextContent(type="text", text=output)]

    elif name == "normalize":
        attribute_name = arguments["attribute_name"]
        patterns = arguments["patterns"]

        # Convert patterns to CAMP format
        rules = []
        for pattern in patterns:
            rules.append({
                "match": pattern["match"],
                "replace": pattern["replace"],
                "isDefault": pattern.get("isDefault", False)
            })

        step_config = {
            "mutations": [
                {
                    "inputField": "value",
                    "outputField": "normalized_value",
                    "rules": rules
                }
            ]
        }

        # Return JSON in hidden format for Claude to extract internally
        output = f"""✓ Normalization step configured

Applying {len(rules)} regex pattern(s) to standardize values.

<step_config>
{json.dumps(step_config, indent=2)}
</step_config>
"""

        return [TextContent(type="text", text=output)]

    elif name == "publish":
        attribute_name = arguments["attribute_name"]
        mappings = arguments.get("mappings", [])

        # Default mappings if none provided
        if not mappings:
            mappings = [
                {
                    "attributeName": attribute_name,
                    "campField": "normalized_value",
                    "required": False
                },
                {
                    "attributeName": "camp_ai_reasoning",
                    "campField": "reasoning",
                    "required": False
                },
                {
                    "attributeName": "camp_ai_value",
                    "campField": "value",
                    "required": False
                }
            ]

        step_config = {
            "data": mappings,
            "productIdField": "entity_id",
            "retailerIdField": "",
            "localeField": "",
            "useRetailerId": False,
            "useLocale": False
        }

        # Return JSON in hidden format for Claude to extract internally
        output = f"""✓ Publish step configured

Publishing {len(mappings)} field(s) to Snowflake catalog.

<step_config>
{json.dumps(step_config, indent=2)}
</step_config>
"""

        return [TextContent(type="text", text=output)]

    elif name == "assemble_pipeline":
        pipeline_name = arguments["name"]
        description = arguments.get("description", "")
        steps = arguments["steps"]

        # Generate UUIDs for each step
        pipeline_steps = []
        prev_step_id = None
        first_step_id = None

        for idx, step in enumerate(steps):
            step_id = str(uuid.uuid4())
            if idx == 0:
                first_step_id = step_id

            pipeline_step = {
                "pipelineStepId": step_id,
                "stepId": str(idx + 1),  # Sequential step IDs
                "stepVersionId": str(1000 + idx),  # Placeholder version IDs
                "version": "1",
                "type": "task",
                "attributeOverrides": {},
                "nextStepsRule": None
            }

            # Connect to next step
            if idx < len(steps) - 1:
                next_step_id = str(uuid.uuid4())
                pipeline_step["nextStepsRule"] = {
                    "type": "singleNextStep",
                    "nextStep": next_step_id,
                    "possibleNextSteps": [next_step_id]
                }
                # Store for next iteration
                prev_step_id = next_step_id

            # Use the stored ID for non-first steps
            if idx > 0:
                pipeline_steps[-1]["nextStepsRule"]["nextStep"] = step_id
                pipeline_steps[-1]["nextStepsRule"]["possibleNextSteps"] = [step_id]

            pipeline_steps.append(pipeline_step)

        pipeline_orchestration = {
            "firstPipelineStepId": first_step_id,
            "enableSchedule": False,
            "hoursInterval": 24,
            "cronError": None,
            "steps": pipeline_steps
        }

        output = f"""# Complete Pipeline Assembly

## Pipeline: {pipeline_name}

{description}

## Pipeline Orchestration JSON

```json
{json.dumps(pipeline_orchestration, indent=2)}
```

## Individual Step Configurations

"""
        for idx, step in enumerate(steps, 1):
            output += f"### Step {idx} Configuration\n\n```json\n{json.dumps(step, indent=2)}\n```\n\n"

        output += """---

**Pipeline is ready!**

This pipeline is:
- ✅ Not scheduled (manual runs only)
- ✅ Connected with proper step flow
- ✅ Ready to import into CAMP

You can now copy the configurations and import them into CAMP.
"""

        return [TextContent(type="text", text=output)]

    elif name == "models":
        output = "# Available CAMP Models\n\n"
        for model, info in sorted(AVAILABLE_MODELS.items(), key=lambda x: x[1]["usage"], reverse=True):
            output += f"**{model}** (Used in {info['usage']} pipelines)\n"
            output += f"  - {info['description']}\n\n"

        return [TextContent(type="text", text=output)]

    elif name == "explain_modes":
        mode = arguments.get("mode", "all")

        if mode == "all":
            output = "# CAMP Operation Modes\n\n"
            output += "**sync:** " + OPERATION_MODES["sync"] + "\n\n"
            output += "**batch:** " + OPERATION_MODES["batch"] + "\n\n"
            output += "**null:** " + OPERATION_MODES["null"] + "\n\n"
            output += "## Usage Statistics:\n"
            output += "- No mode specified (null/null): 59 pipelines - Uses pipeline defaults\n"
            output += "- Sync/Sync: 38 pipelines - Real-time testing\n"
            output += "- Batch/Sync: 20 pipelines - Production batch with sync testing\n"
            output += "- Batch/Batch: 10 pipelines - Full batch mode\n"
        else:
            output = f"**{mode}:** {OPERATION_MODES.get(mode, 'Unknown mode')}\n"

        return [TextContent(type="text", text=output)]

    elif name == "step_types":
        output = "# Available CAMP Step Types\n\n"
        for step_type, description in STEP_TYPES.items():
            output += f"**{step_type}:** {description}\n\n"

        return [TextContent(type="text", text=output)]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
