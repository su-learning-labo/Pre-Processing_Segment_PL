import subprocess

if __name__ == "__main__":
    cmd = 'streamlit run main.py'
    subprocess.call(cmd.split())