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

find "$DIR" -name "*.fmp12" ! -name "dev.fmp12" -type f -mtime +14 -exec rm {} +
