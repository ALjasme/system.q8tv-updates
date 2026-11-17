# Monthly photos

`photos.json` lists the Kuwait photos the home screens add to their wallpaper rotation, with each author,
licence and Wikimedia Commons source. The files are assets of the `photos-YYYY-MM` releases.

On the 1st of each month `.github/workflows/monthly-photos.yml` publishes the next four photos of
`queue.json`: photos reviewed by eye beforehand (Kuwait only, no people), whose free licence is checked
again before publishing. When the queue is empty the job opens an issue instead of choosing unreviewed photos.
`skip.txt` lists Commons files never to use (already bundled in the app).
