# Motion Task Automation CLI

## Overview

This command-line interface (CLI) Python script automates task collection management within the Motion platform. It allows users to:

*   Pull tasks as a collection from an existing Motion project and save them as a template (`.json`) in the `./templates/` directory.
*   Create new Motion tasks in bulk from a saved task template, choosing a schedule, new project, and/or setting a future due date.

## Prerequisites

*   Python
*   A Motion account and a valid API Key.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

 Set the `MOTION_API_KEY` environment variable to your Motion API Key.

```bash
export MOTION_API_KEY="YOUR_API_KEY"
```

## Usage

```bash
python task_templating.py
```


## Rate Limiting

*   The Motion API is limited to 12 requests per minute.
    *   This script implements an 8-second delay between task creation requests to accomidate this.