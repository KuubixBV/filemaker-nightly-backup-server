#!/bin/bash
while getopts t: flag
do
    case "${flag}" in
        t) type=${OPTARG};;
    esac
done

cd /home/kuadmin/dev/filemaker-nightly-backup-server
if [[ $type = "files" ]]
then
	echo "FILES"
	source ./backup_env/bin/activate
	python ./clone_backup.py --backup-type files
	deactivate
elif [[ $type = "database" ]]
then
	echo "DATABASE"
	source ./backup_env/bin/activate
	python ./clone_backup.py --backup-type database
	deactivate
else
    echo "Invalid flag value, accepted values are 'files,database'."
fi
