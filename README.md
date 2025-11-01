# KiCAD-Chat

A minimal, single-file chatbot for querying KiCad schematic files using natural language powered by OpenAI's GPT-4. Ask questions like "What's connected to U1 pin 7?" or "List all resistors" and get instant answers about your electronics designs.

## ✨ Features

- **Natural Language Queries**: Ask questions in plain English about components, nets, and connections
- **Direct S-Expression Parsing**: Parses `.kicad_sch` files without requiring KiCad installation
- **OpenAI GPT-4 Integration**: Leverages advanced AI for accurate, contextual responses
- **CLI Interface**: Simple command-line tool with rich formatting
- **Minimal Dependencies**: Just 4 Python packages for maximum portability
- **Industrial Scale**: Handles schematics with hundreds of components
- **Tool-Based Reasoning**: Uses function calling for precise schematic analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- OpenAI API key

### Installation
```bash
git clone https://github.com/WilliamxLeismer/KiCAD-Chat.git
cd KiCAD-Chat
pip install -r requirements.txt
```

### Setup
1. Copy `.env.example` to `.env`
2. Add your OpenAI API key: `OPENAI_API_KEY=sk-your-key-here`

### Usage
```bash
# Interactive mode
python kicad_chat.py your_schematic.kicad_sch

# Piped input for automation
echo "How many capacitors are there?" | python kicad_chat.py schematic.kicad_sch
```

## 💡 Example Queries

- "What components are in this schematic?"
- "Tell me about R1"
- "List all resistors and their values"
- "Find the power supply nets"
- "Trace the VCC net"
- "What is connected to pin 7 of U1?"

## 🏗️ How It Works

**Single-file MVP approach** - No unnecessary complexity:

- **Parser**: Direct S-expression parsing of KiCad files
- **Tools**: 7 core functions for schematic queries
- **LLM**: OpenAI GPT-4 with function calling
- **Interface**: Rich CLI with Markdown output

## 🤝 Contributing

This is a minimal MVP - contributions welcome! Areas for improvement:
- Enhanced connection tracing algorithms
- Support for hierarchical sheets
- Visual diagram generation
- Performance optimizations
- Chat with your PCB

## 📄 License

MIT License - Free for personal and commercial use.
