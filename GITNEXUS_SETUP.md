# GitNexus Setup Guide for Project Music

## What is GitNexus?

GitNexus builds a knowledge graph of your codebase - tracking every dependency, call chain, and execution flow. It gives AI agents (like me!) deep architectural awareness of your code.

## Quick Setup

### 1. Analyze Your Project

Run this command from your project root:

```bash
npx gitnexus@latest analyze
```

This will:
- Index your entire codebase
- Build a knowledge graph of all code relationships
- Create execution flow maps
- Generate AI context files (AGENTS.md, CLAUDE.md)
- Set up agent skills for code exploration

### 2. Configure MCP (Model Context Protocol)

To connect GitNexus with AI editors like Claude Code or Cursor:

```bash
npx gitnexus@latest setup
```

This auto-detects your editors and configures them to use GitNexus.

### 3. List Indexed Repositories

```bash
npx gitnexus@latest list
```

### 4. Check Index Status

```bash
npx gitnexus@latest status
```

## What GitNexus Provides

### 7 Powerful Tools:

1. **`query`** - Process-grouped hybrid search (BM25 + semantic)
2. **`context`** - 360-degree symbol view with categorized references
3. **`impact`** - Blast radius analysis (what breaks if you change X?)
4. **`detect_changes`** - Git-diff impact mapping
5. **`rename`** - Multi-file coordinated renaming
6. **`cypher`** - Raw graph queries
7. **`list_repos`** - Discover all indexed repositories

### 4 Agent Skills:

- **Exploring** - Navigate unfamiliar code
- **Debugging** - Trace bugs through call chains
- **Impact Analysis** - Analyze blast radius before changes
- **Refactoring** - Plan safe refactors using dependency mapping

## Use Cases for Your Music Project

### 1. Understanding OnTheSpot Architecture

```bash
# Query how authentication works
npx gitnexus@latest tool query --query "spotify authentication flow"

# Get context on a specific function
npx gitnexus@latest tool context --name "download_track"
```

### 2. Impact Analysis Before Changes

```bash
# See what depends on a function before modifying it
npx gitnexus@latest tool impact --target "UserService" --direction "upstream"

# Check what your current changes affect
npx gitnexus@latest tool detect_changes --scope "all"
```

### 3. Safe Refactoring

```bash
# Rename a function across all files
npx gitnexus@latest tool rename --symbol_name "old_name" --new_name "new_name" --dry_run true
```

### 4. Generate Documentation

```bash
# Create a wiki from your knowledge graph
npx gitnexus@latest wiki
```

## Web UI (Alternative)

If you prefer a visual interface:

1. Visit: https://gitnexus.vercel.app
2. Drag & drop your project as a ZIP file
3. Explore the interactive knowledge graph

Or run locally:

```bash
cd GitNexus-main/gitnexus-web
npm install
npm run dev
```

## Supported Languages

- ✅ Python (OnTheSpot)
- ✅ JavaScript/TypeScript (Web UI)
- ✅ Java, C, C++, C#, Go, Rust

## Next Steps

1. **Run the analysis**: `npx gitnexus@latest analyze`
2. **Explore the graph**: Check the generated `.gitnexus/` folder
3. **Read the context files**: Open `AGENTS.md` and `CLAUDE.md`
4. **Try a query**: Use the tools to explore your codebase

## Troubleshooting

### Analysis is slow?
- Skip embeddings for faster indexing: `npx gitnexus@latest analyze --skip-embeddings`
- Force re-index: `npx gitnexus@latest analyze --force`

### Clean up?
```bash
# Remove index for current repo
npx gitnexus@latest clean

# Remove all indexes
npx gitnexus@latest clean --all --force
```

## Privacy & Security

- ✅ Everything runs locally
- ✅ No network calls
- ✅ Index stored in `.gitnexus/` (gitignored)
- ✅ Open source - audit the code yourself

## Resources

- GitHub: https://github.com/abhigyanpatwari/gitnexus
- Web UI: https://gitnexus.vercel.app
- Documentation: See GitNexus-main/README.md

