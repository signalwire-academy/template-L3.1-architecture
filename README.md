# Lab 3.1: Enterprise Architecture

**Duration:** 90 minutes
**Level:** 3

## Objectives

Complete this lab to demonstrate your understanding of the concepts covered.

## Prerequisites

- Completed previous labs
- Python 3.10+ with signalwire-agents installed
- Virtual environment activated

## Instructions

### 1. Set Up Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Implement Your Solution

Edit `solution/agent.py` according to the lab requirements.

### 3. Test Locally

```bash
# List available functions
swaig-test solution/agent.py --list-tools

# Check SWML output
swaig-test solution/agent.py --dump-swml
```

### 4. Submit

```bash
git add solution/agent.py
git commit -m "Complete Lab 3.1: Enterprise Architecture"
git push
```

## Grading

| Check | Points |
|-------|--------|
| Agent Instantiation | 20 |
| SWML Generation | 20 |
| route_call function | 30 |
| Agent Transfer | 30 |
| **Total** | **100** |

**Passing Score:** 70%

## Reference

See `reference/starter.py` for a boilerplate template.

---

*SignalWire AI Agents Certification*
