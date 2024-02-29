#!/bin/bash
while getopts "d:" opt; do
  case $opt in
    d)
      DIR=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      ;;
  esac
done

sudo chown -R fmserver:fmsadmin /opt/FileMaker/FileMaker\ Server/Data/Databases
sudo chmod -R 750 "$DIR"
