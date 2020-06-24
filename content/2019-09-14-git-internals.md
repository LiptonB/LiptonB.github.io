Title: Git internals
Category: tools
Status: draft

Talk Outline
============
- Commit history stuff (branches, merges, rebase, blah blah)
- Data storage stuff (index, objects, packing)
- Merges and merge conflicts
- Git LFS
- Tips
  - git add -p
  - gitk/git instaweb/git log --graph --decorate
  - git log --name-status


Notes
=====
Types of object:
- blobs (file data, zlib compressed)
- trees (directories - contain names, modes, shas of blobs and other trees. also zlib compressed)
- commits (author, committer, parent, message, and a single tree (representing root dir))
- tags (reference to another object with message, tagger, tag)

Index: binary format that contains the information needed to make a tree

Pack files:
- .pack contains a bunch of object records (does not include the object sha)
- .idx contains object shas and offsets into the .pack file
- can be delta compressed - binary delta where options are "copy data from source object" and "insert the following data"

References:
- https://github.com/pluralsight/git-internals-pdf
- https://git-scm.com/book/en/v1/Git-Internals-Plumbing-and-Porcelain
