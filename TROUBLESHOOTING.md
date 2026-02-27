# TROUBLESHOOTING.md

## Agent Setup
To set up the Biocore agent, follow these steps:
1. Clone the repository:
   ```bash
   git clone https://github.com/Hanishchow/Biocore-agent.git
   cd Biocore-agent
   ```
2. Install the necessary dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your environment variables as required by the agent.
   
## Running the Agent
To run the agent, use the following command:
```bash
python run_agent.py
```

## Common Issues and Fixes
- **Issue:** Agent fails to start.
  - **Fix:** Ensure all dependencies are installed and your environment variables are correctly set.
- **Issue:** Performance issues.
  - **Fix:** Check your system resources and optimize configurations according to the documentation.

## Environment Setup
Make sure to have the following in your environment:
- Python 3.8 or higher
- Compatible libraries as listed in requirements.txt
- Proper access permissions to the necessary directories

## Debugging Tips
- Run the agent with debug mode enabled to gather more information:
```bash
python run_agent.py --debug
```
- Check the logs in the `logs/` directory for additional error messages.
