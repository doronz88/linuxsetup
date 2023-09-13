# Overview

Setup script for quickly setting up linux installations for a more efficient work computer.

<details>
<summary>Show what installation includes</summary>

- git
- git-lfs
- jq
- cmake
- ripgrep
- bat
- fzf
- xonsh
- wget
- htop
- ncdu
- watch
- bash-completion
- nodejs
- PyCharm CE
- Visual Studio Code
- Sublime Text
- Wireshark
- xonsh

</details>

# Perquisites

- Execute:
    ```shell
    sudo apt update
    sudo apt install python3 python3-git git
    ssh-keygen
    cat ~/.ssh/id_rsa.pub
    ```

- [Then paste the `cat` result into your GitHub SSH keys](https://github.com/settings/ssh/new)

- Execute the following:
  ```shell
  mkdir ~/dev
  cd ~/dev
  git clone git@github.com:doronz88/linuxsetup.git
  cd linuxsetup
  python3 -m pip install -r requirements.txt
  ```

# Usage

```shell
# pass -a/--automated for doing everything without prompting (unless certain removals are required)
python3.11 install_linux.py everything
```
