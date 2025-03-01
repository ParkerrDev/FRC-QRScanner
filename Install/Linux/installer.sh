#!/usr/bin/env bash

set -euo pipefail

src_dir=$(pwd)
readonly dst_dir="/usr/local"

print_in_color() {
  local color=$1
  shift
  echo -e "\e[${color}m$@\e[0m"
}

install_rpm() {
  sudo dnf install python3 -y
  sudo dnf install python3-pip -y
  sudo dnf install PyQt5 -y
  sudo dnf install python3-zbar -y
  cd ..
  cd ..
  pip3 install -r requirements.txt || exit 1
  mkdir -p ~/.icons && print_in_color "1;37" "Icon directory created."
  cp Assets/1671-icon.png ~/.icons
  cp Install/Linux/QRScanner.desktop ~/.local/share/applications
  sudo mkdir "$dst_dir/1671-QR-Code-Scanner"
  sudo cp -r * "$dst_dir/1671-QR-Code-Scanner"
  print_in_color "1;32" "Succesfully installed 1671-QR-Code-Scanner"
}

uninstall_rpm() {
  #pip3 uninstall -r requirements.txt || exit 1
  rm -f ~/.icons/1671-icon.png
  rm -f ~/.local/share/applications/QRScanner.desktop
  sudo rm -rf "$dst_dir/1671-QR-Code-Scanner"
  print_in_color "1;32" "Succesfully uninstalled 1671-QR-Code-Scanner"
}

reinstall_rpm() {
  uninstall_rpm
  install_rpm
  exit
}

#install_deb() {
#  if ! command -v tilix > /dev/null; then
#    sudo apt-get update
#    sudo apt-get install tilix -y
#  fi
#
#  if ! command -v python3 > /dev/null; then
#    sudo apt-get install python3 -y
#  fi
#
#  if ! command -v pip3 > /dev/null; then
#    sudo apt-get install python3-pip -y
#  fi
#
#  if ! command -v python3-tkinter > /dev/null; then
#    sudo apt-get install python3-tkinter -y
#  fi
#
#  pip3 install -r requirements.txt || exit 1
#  cp Assets/1671-icon.png ~/.icons
#  cp Assets/QRScanner.desktop ~/.local/share/applications
#  sudo mkdir "$dst_dir/1671-QR-Code-Scanner"
#  sudo cp -r * "$dst_dir/1671-QR-Code-Scanner"
#  print_in_color "1;32" "Succesfully installed 1671-QR-Code-Scanner"
#}

#uninstall_deb() {
#  #pip3 uninstall -r requirements.txt || exit 1
#  rm -f ~/.icons/1671-icon.png
#  rm -f ~/.local/share/applications/QRScanner.desktop
#  sudo rm -rf "$dst_dir/1671-QR-Code-Scanner"
#  print_in_color "1;32" "Succesfully uninstalled 1671-QR-Code-Scanner"
#}

main() {
  if [[ $# -ne 1 ]]; then
    echo "Usage: $0 {install|uninstall|reinstall}"
    exit 1
  fi

  case "$1" in
    install)
      if [[ -f /etc/debian_version ]]; then
        install_deb
      else
        install_rpm
      fi
      ;;
    uninstall)
      if [[ -f /etc/debian_version ]]; then
        uninstall_deb
      else
        uninstall_rpm
      fi
      ;;
      reinstall)
      if [[ -f /etc/debian_version ]]; then
        reinstall_deb
      else
        reinstall_rpm
      fi
      ;;
    *)
      echo "Usage: $0 {install|uninstall|reinstall}"
      exit 1
      ;;
  esac
}

main "$@"
