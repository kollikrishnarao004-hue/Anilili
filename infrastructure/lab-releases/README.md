# Private release repository workflow templates

Copy `.github/workflows/lab-candidate.yml` and `lab-publish.yml` into the private
`kollikrishnarao004-hue/Anilili-Lab-Releases` repository on its `main` branch.
These do not run in the public source repository. Both are manually dispatched;
only the second publishes an approved APK to the private update channel.

The source is checked out from `kollikrishnarao004-hue/Anilili`. Candidates require the
full current source `main` commit, and the manifest records that exact source revision
as well as the private workflow repository revision. Signing secrets exist only in
the private repository. Read `docs/LAB-RELEASES.md` in the source repository for setup.
