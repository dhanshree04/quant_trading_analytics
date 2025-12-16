import os
import subprocess
import sys

def main():
    print("Starting Quant Analytics Dashboard...")
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
        
    app_path = os.path.join("src", "app.py")
    
    # Use 'streamlit run src/app.py'
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
