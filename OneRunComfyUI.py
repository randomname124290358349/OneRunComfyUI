#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
import os
import subprocess
import urllib.request
import json
import logging
import sys
import zipfile
import shutil
from pathlib import Path

def setup_logger():
    logger = logging.getLogger('OneRunComfyUI')
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '\033[92m%(asctime)s\033[0m - \033[94m%(name)s\033[0m - \033[93m%(levelname)s\033[0m - %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

def download_file(url, filepath, logger):
    if os.path.exists(filepath):
        logger.info(f"File already exists: {os.path.basename(filepath)}")
        return True
    
    logger.info(f"Downloading: {os.path.basename(filepath)}")
    try:
        urllib.request.urlretrieve(url, filepath)
        logger.info(f"Download completed: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        logger.error(f"Error downloading {os.path.basename(filepath)}: {e}")
        return False

def download_7zip(logger):
    zip_file = "7zr.exe"
    url = "https://www.7-zip.org/a/7zr.exe"
    
    logger.info("Downloading 7zip extractor...")
    if download_file(url, zip_file, logger):
        return zip_file
    return None

def setup_curl(logger):
    """Setup curl executable, using system curl if available or downloading if needed"""
    
    # First, try to use system curl
    try:
        subprocess.run(['curl', '--version'], capture_output=True, check=True)
        logger.info("Using system curl")
        return 'curl'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check if we already have curl.exe in current directory
    if os.path.exists("curl.exe"):
        logger.info("curl.exe already available in current directory")
        return "curl.exe"
    
    # Download and extract curl
    zip_file = "curl-8.15.0_4-win64-mingw.zip"
    url = "https://curl.se/windows/dl-8.15.0_4/curl-8.15.0_4-win64-mingw.zip"
    
    logger.info("Downloading curl...")
    try:
        if not download_file(url, zip_file, logger):
            return None
        
        logger.info("Extracting curl...")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        # Find curl.exe in extracted folders
        curl_path = None
        for root, dirs, files in os.walk("."):
            if "curl.exe" in files:
                curl_path = os.path.join(root, "curl.exe")
                break
        
        if curl_path:
            # Move curl.exe to current directory
            shutil.move(curl_path, "curl.exe")
            curl_path = "curl.exe"
        
        # Clean up
        try:
            os.remove(zip_file)
            # Remove extracted folders
            for item in os.listdir("."):
                if os.path.isdir(item) and "curl" in item.lower():
                    shutil.rmtree(item)
        except Exception:
            pass
        
        if curl_path and os.path.exists("curl.exe"):
            logger.info("curl extracted successfully")
            return "curl.exe"
        else:
            logger.error("Failed to extract curl.exe")
            return None
            
    except Exception as e:
        logger.error(f"Error setting up curl: {e}")
        return None

def setup_git(logger):
    """Setup git executable, using system git if available or downloading if needed"""
    
    # First, try to use system git
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        logger.info("Using system git")
        return 'git'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check if we already have portable git installed
    git_portable_path = os.path.join("git_portable", "bin", "git.exe")
    if os.path.exists(git_portable_path):
        logger.info("Portable git already available")
        return os.path.abspath(git_portable_path)
    
    logger.info("Downloading Git for Windows...")
    
    try:
        # Get latest Git for Windows portable version
        request = urllib.request.Request(
            "https://api.github.com/repos/git-for-windows/git/releases/latest",
            headers={'User-Agent': 'ComfyUI-Installer'}
        )
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
            filename, url = None, None
            
            # Look for PortableGit 64-bit
            for asset in data.get('assets', []):
                asset_name = asset.get('name', '')
                if 'PortableGit' in asset_name and '64-bit' in asset_name and asset_name.endswith('.7z.exe'):
                    filename = asset_name
                    url = asset.get('browser_download_url')
                    break
            
            if not filename or not url:
                logger.error("Could not find Git portable version")
                return None
            
            logger.info(f"Downloading {filename}...")
            if not download_file(url, filename, logger):
                return None
            
            logger.info("Extracting Git...")
            # PortableGit is self-extracting, extract to git_portable folder
            subprocess.run([filename, '-o', 'git_portable', '-y'], check=True)
            
            # Find git.exe in extracted folder
            git_path = os.path.join("git_portable", "bin", "git.exe")
            if os.path.exists(git_path):
                git_exe_path = os.path.abspath(git_path)
                logger.info("Git extracted successfully")
            else:
                logger.error("git.exe not found in extracted files")
                return None
            
            # Clean up only the installer file
            try:
                os.remove(filename)
            except Exception:
                pass
            
            return git_exe_path
            
    except Exception as e:
        logger.error(f"Error setting up git: {e}")
        return None

def install_comfyui(logger):
    if os.path.exists("ComfyUI_windows_portable"):
        logger.info("ComfyUI is already installed")
        return True
    
    logger.info("Starting ComfyUI installation...")
    
    # Setup curl
    curl_exe = setup_curl(logger)
    if not curl_exe:
        logger.error("Failed to setup curl")
        return False
    
    # Download 7zip
    zip_exe = download_7zip(logger)
    if not zip_exe:
        logger.error("Failed to download 7zip")
        return False
    
    try:
        logger.info("Getting latest ComfyUI version...")
        request = urllib.request.Request(
            "https://api.github.com/repos/comfyanonymous/ComfyUI/releases/latest",
            headers={'User-Agent': 'ComfyUI-Installer'}
        )
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
            filename, url = None, None
            
            for asset in data.get('assets', []):
                if asset.get('name', '').endswith('.7z'):
                    filename = asset.get('name')
                    url = asset.get('browser_download_url')
                    break
            
            if not filename or not url:
                logger.error("Could not get latest version")
                return False
            
            logger.info(f"Downloading {filename}...")
            if curl_exe == 'curl':
                subprocess.run(['curl', '-L', '--progress-bar', '--fail', '-o', filename, url], check=True)
            else:
                subprocess.run([curl_exe, '-L', '--progress-bar', '--fail', '-o', filename, url], check=True)
            
            if os.path.getsize(filename) < 1048576:
                logger.error("Invalid file (too small)")
                os.remove(filename)
                return False
            
            logger.info(f"Extracting {filename}...")
            subprocess.run([f'./{zip_exe}', 'x', filename, '-bso0', '-y'], check=True)
            
            # Clean up files
            try:
                os.remove(filename)
                os.remove(zip_exe)
                if os.path.exists("curl.exe"):
                    os.remove("curl.exe")
                logger.info("Temporary files removed")
            except Exception:
                pass
            
            logger.info("ComfyUI installed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Error during installation: {e}")
        try:
            if os.path.exists(zip_exe):
                os.remove(zip_exe)
            if os.path.exists("curl.exe"):
                os.remove("curl.exe")
        except Exception:
            pass
        return False


def download_custom_nodes(logger, custom_nodes_git_urls):
    logger.info("Starting custom nodes downloads...")
    root_comfyui_path = "ComfyUI_windows_portable/ComfyUI"
    custom_nodes_dir  = os.path.join(root_comfyui_path, "custom_nodes")
    
    # Create directories if they don't exist
    Path(custom_nodes_dir).mkdir(parents=True, exist_ok=True)
    
    # Setup git
    git_exe = setup_git(logger)
    if not git_exe:
        logger.error("Failed to setup git")
        return False
    
    # Store current directory to restore later
    original_dir = os.getcwd()
    
    success_count = 0
    for url in custom_nodes_git_urls:
        try:
            # Extract repository name from URL
            repo_name = url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(custom_nodes_dir, repo_name)
            
            # Skip if already exists
            if os.path.exists(repo_path):
                logger.info(f"Custom node already exists: {repo_name}")
                success_count += 1
                continue
            
            logger.info(f"Cloning custom node: {repo_name}")
            
            # Change to custom_nodes directory
            os.chdir(custom_nodes_dir)
            
            # Clone the repository using absolute path for git
            subprocess.run([
                git_exe, 'clone', '--quiet', '--no-progress', url, repo_name
            ], check=True)
            
            # Return to original directory
            os.chdir(original_dir)
            
            logger.info(f"Successfully cloned: {repo_name}")
            success_count += 1
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone {url}: {e}")
            # Make sure we're back in original directory
            os.chdir(original_dir)
        except Exception as e:
            logger.error(f"Error cloning {url}: {e}")
            # Make sure we're back in original directory
            os.chdir(original_dir)
    
    # Clean up git portable if we downloaded it
    try:
        if git_exe != "git" and os.path.exists("git_portable"):
            shutil.rmtree("git_portable")
            logger.info("Temporary git portable removed")
    except Exception:
        pass
    
    logger.info(f"Custom nodes downloaded: {success_count}/{len(custom_nodes_git_urls)}")
    return success_count == len(custom_nodes_git_urls)


def download_models(logger, models):
    logger.info("Starting model downloads...")
    
    root_comfyui_path = "ComfyUI_windows_portable/ComfyUI"
    models_dir        = os.path.join(root_comfyui_path, "models")
    checkpoints_dir   = os.path.join(models_dir,        "checkpoints")
    upscale_dir       = os.path.join(models_dir,        "upscale_models")
    
    # Create directories if they don't exist
    Path(checkpoints_dir).mkdir(parents=True, exist_ok=True)
    Path(upscale_dir).mkdir(parents=True, exist_ok=True)
    
    # Dict mapping
    directory_mapping = {
        "checkpoints_dir": checkpoints_dir,
        "upscale_dir": upscale_dir
    }
    
    success_count = 0
    for model in models:
        # Resolve o diretório baseado na string
        target_dir = directory_mapping.get(model["directory"], model["directory"])
        filepath = os.path.join(target_dir, model["filename"])
        if download_file(model["url"], filepath, logger):
            success_count += 1
    
    logger.info(f"Models downloaded: {success_count}/{len(models)}")
    return success_count == len(models)

def main():
    logger = setup_logger()
    
    logger.info("Starting ComfyUI setup")
    
    # Install ComfyUI
    if not install_comfyui(logger):
        logger.error("ComfyUI installation failed")
        sys.exit(1)

    # Here come custom node git urls
    custom_nodes_git_urls = [
        "https://github.com/ltdrdata/ComfyUI-Manager",
        # Add more links here.
    ]
    
    # Download custom nodes
    if not download_custom_nodes(logger, custom_nodes_git_urls):
        logger.warning("Some custom nodes failed to download")

    # Here come models urls
    models = [

        #{
        #    "url": "https://huggingface.co/cyberdelia/CyberRealisticPony/resolve/main/CyberRealisticPony_V12.7_FP16.safetensors?download=true",
        #    "filename": "CyberRealisticPony_V12.7_FP16.safetensors",
        #    "directory": "checkpoints_dir"
        #},

        # Example of usage.
        #{
        #    "url": "https://civitai.com/api/download/models/164821?type=Model&format=PickleTensor",
        #    "filename": "remacri_original.pt",
        #    "directory": "upscale_dir"
        #}
    ]

    # Download models
    if not download_models(logger, models):
        logger.warning("Some models failed to download")
    
    logger.info("ComfyUI setup completed!")

if __name__ == "__main__":
    main()