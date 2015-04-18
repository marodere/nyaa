#!/usr/bin/env bash

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/bin"
export LC_ALL="ru_RU.UTF-8"

function log_message() {
	printf "%s > %s\n" "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

cd ${HOME}/anime-fetch

(
	flock -n 9 || exit 0
	exec 1>>nyaa.log 2>&1
	if [ -f 'flags/nyaa.stop' ]; then
		exit 0
	fi
	cp nyaa.json nyaa.json.bak
	log_message started
	./nyaa.py
	err=$?
	log_message finished with status $err
	exit $err
) 9>flags/nyaa.lck

if [ $? -ne 0 ]; then
	touch flags/nyaa.stop
	tail -n 10 nyaa.log
fi
