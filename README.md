<div align="center">

<img width="489" height="162" alt="image" src="https://github.com/user-attachments/assets/8a61c5a0-d1e6-4de5-a261-6897c18c2830" />



# Topic2Manim

</div>

Automatic educational video generator using AI and Manim. Converts any topic into a professional animated video with narration and mathematical visualizations.

<div align="center">
  
## User Interface

![video](./public/output6.gif)

</div>

<div align="center">
  
## Examples

</div>

> propmt: How do machines learn to recognize MNIST dataset numbers?
> 
> model: claude-sonnet-4-5-20250929
> 
> response:

<div align="center">

![video](./public/output5.gif)

</div>

> propmt: What is a Markov chain and how are they related to LLMs?
> 
> model: claude-sonnet-4-5-20250929
> 
> response:

<div align="center">

![video](./public/output4.gif)

</div>

> propmt: How does Cramer's rule work for system of linear equations?
> 
> model: claude-sonnet-4-5-20250929
> 
> response:

<div align="center">

![video](./public/output3.gif)

</div>

> propmt: how chat gpt works?
> 
> model: gpt-5.2
> 
> response:

<div align="center">

![video](./public/output.gif)

</div>

> propmt: how tokenization works in chat gpt?
> 
> model: gpt-5.2
> 
> response:

<div align="center">

![video](./public/output2.gif)

</div>

## Features

- **Multi-LLM Support** with automatic fallback (OpenAI GPT, Claude)
- **Automatic script generation** using advanced language models
- **Educational animations** with Manim Community Edition
- **Multi-language support** (automatically detects topic language)
- **Optimized videos** of ~60 seconds with multiple scenes
- **Automatic concatenation** of fragments into final video

## Architecture

### System Overview

Topic2Manim is a multi-agent system that orchestrates several specialized components to transform a topic into an educational video. The system follows a pipeline architecture where each agent has a specific responsibility.

```mermaid
graph TB
    subgraph Input
        A[User Topic]
    end
    
    subgraph "LLM Configuration"
        B[setup_llm_client]
        B1[Claude API]
        B2[OpenAI API]
        B -->|Priority 1| B1
        B -->|Fallback| B2
    end
    
    subgraph "Agent 1: Script Generation"
        C[animations.py]
        C1[generate_script_json]
        C --> C1
    end
    
    subgraph "Agent 2: TTS Generation"
        D[tts_generator.py]
        D1[generate_complete_audio]
        D2[generate_audio_fragment]
        D3[concatenate_audio_fragments]
        D1 --> D2
        D2 --> D3
    end
    
    subgraph "Agent 3: Manim Code Generation"
        E[manim_generator.py]
        E1[generate_manim_code]
        E --> E1
    end
    
    subgraph "Agent 4: Video Compilation"
        F[concat_video.py]
        F1[compile_video]
        F2[concatenate_videos]
        F3[merge_video_and_audio]
        F1 --> F2
        F2 --> F3
    end
    
    subgraph Output
        G[Final Video with Audio]
    end
    
    A --> B
    B --> C1
    C1 -->|video-output.json| D1
    C1 -->|video-output.json| E1
    D1 -->|audio durations| E1
    E1 -->|.py files| F1
    F1 -->|.mp4 fragments| F2
    D3 -->|audio.mp3| F3
    F2 -->|output_silent.mp4| F3
    F3 --> G
    
    style A fill:#e1f5ff
    style G fill:#c8e6c9
    style C fill:#fff9c4
    style D fill:#ffe0b2
    style E fill:#f8bbd0
    style F fill:#d1c4e9
```

## Installation

First, install uv (if you haven't already):

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

### Setup

```bash
git clone https://github.com/mateolafalce/topic2manim.git
cd topic2manim

# Create virtual environment and install all dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

cp .env.example .env
```

## Usage

Start the Flask server:

```bash
python src/main.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

or 

```bash
docker compose up
```


