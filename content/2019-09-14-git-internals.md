Title: Git internals
Category: tools
Status: draft

Talk Outline
============
- My first commit
  - clone
  - (edit)
  - commit -a
  - (edit)
  - add
  - commit
  - push
- More interactions
  - pull
  - log
  - (edit)
  - status
  - add -p
  - commit
  - push (out of date)
  - pull
  - push
- Working on a branch
- Merge conflict
- Commit history stuff (branches, merges, rebase, blah blah)
  - A commit points to a version of the repository
  - Commits have parents
  - A branch points to a commit
- Data storage stuff (index, objects, packing)
- Merges and merge conflicts
- Git LFS
- Tips
  - git add -p
  - gitk/git instaweb/git log --graph --decorate
  - git log --name-status


Notes
=====
General approach ideas:
- Walk through using the repo, with gradually more advanced examples
  - Show a running visualization of the repo
- Divide the commands into groups by concept
- Talk about how it works internally, then do commands

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
