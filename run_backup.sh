#!/bin/bash
while getopts t: flag
do
    case "${flag}" in
        t) type=${OPTARG};;
    esac
done

cd /home/kuadmin/dev/filemaker-nightly-backup-server
if [ $type = "files" ]
then
	echo "FILES"
	./backup_env/bin/python3 ./clone_backup.py --backup-type files
elif [ $type = "database" ]
then
	echo "DATABASE"
	./backup_env/bin/python3 ./clone_backup.py --backup-type database
else
    echo "Invalid flag value, accepted values are 'files,database'."
fi
