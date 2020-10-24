Title: Encrypting a Fedora system post-install (with EFI and btrfs)
Category: system administration
Tags: btrfs, EFI, Fedora, encryption

[TOC]

I had a Fedora 23 system that I decided I would like to be encrypted. I could
have just backed up my documents and reinstalled, but I decided it would be
more interesting to create the encrypted partition myself. I happened to have
decided to try out btrfs when installing this system, which turns out to have
been convenient because a btrfs filesystem can be easily and accurately backed
up to another btrfs filesystem using the `send` and `receive` commands.

The steps below show how to perform this backup, create the encrypted
filesystem, restore the backup onto it, and then fix all the necessary system
files to boot from the new, encrypted filesystem.

# Understanding the filesystem structure

Contents of `/etc/fstab`

    UUID=3563aec8-5a5b-48dd-a949-02de373a943d /                       btrfs   subvol=root     0 0
    UUID=c6a4c58a-b13d-4f93-9841-81b0b04d35ed /boot                   ext4    defaults        1 2
    UUID=1616-FDDC          /boot/efi               vfat    umask=0077,shortname=winnt 0 2
    UUID=3563aec8-5a5b-48dd-a949-02de373a943d /home                   btrfs   subvol=home     0 0
    UUID=2d4bc346-b2f2-4436-b583-230fb1ff5dba swap                    swap    defaults        0 0

Let's check out the structure of this btrfs filesystem:

    $ sudo btrfs subvolume list /
    ID 257 gen 93 top level 5 path root
    ID 258 gen 92 top level 5 path home

What are the physical partitions on the disk?

    $ sudo fdisk -l /dev/sda
    Disk /dev/sda: 20 GiB, 21474836480 bytes, 41943040 sectors
    Units: sectors of 1 * 512 = 512 bytes
    Sector size (logical/physical): 512 bytes / 512 bytes
    I/O size (minimum/optimal): 512 bytes / 512 bytes
    Disklabel type: gpt
    Disk identifier: 3705552A-EB6B-444B-B58E-B4052B51BA48


    Device       Start      End  Sectors  Size Type
    /dev/sda1     2048   411647   409600  200M EFI System
    /dev/sda2   411648  1435647  1024000  500M Linux filesystem
    /dev/sda3  1435648  5629951  4194304    2G Linux swap
    /dev/sda4  5629952 41940991 36311040 17.3G Linux filesystem

# Back up filesystem data

For the next steps I booted from a
Fedora 24 livecd and inserted a USB drive with enough space to hold the
filesystem data.

Create a btrfs partition and mount it:

    $ sudo fdisk /dev/sdb  # create a new linux partition
    $ sudo mkfs.btrfs /dev/sdb1
    $ sudo mkdir /mnt/fedora /mnt/backup
    $ sudo mount /dev/sda4 /mnt/fedora
    $ sudo mount /dev/sdb1 /mnt/backup
    $ ls /mnt/fedora/
    home  root

Create read-only snapshots of the subvolumes:

    $ sudo btrfs subvolume snapshot -r /mnt/fedora/root /mnt/fedora/rootBACKUP
    Create a readonly snapshot of '/mnt/fedora/root' in '/mnt/fedora/rootBACKUP'
    $ sudo btrfs subvolume snapshot -r /mnt/fedora/home /mnt/fedora/homeBACKUP
    Create a readonly snapshot of '/mnt/fedora/home' in '/mnt/fedora/homeBACKUP'

Back up the snapshots to the backup volume

    $ sudo btrfs send /mnt/fedora/rootBACKUP/ | sudo btrfs receive /mnt/backup/
    $ sudo btrfs send /mnt/fedora/homeBACKUP/ | sudo btrfs receive /mnt/backup/

# Create an encrypted filesystem and restore data

First, erase all the unencrypted data on the partition.

    $ sudo dd if=/dev/zero of=/dev/sda4

Format/encrypt the partition as a LUKS volume. You will be asked to set a passphrase.

    $ sudo cryptsetup luksFormat /dev/sda4

Unlock the volume. The decrypted partition will be accessible as `/dev/mapper/fedora`.

    $ sudo cryptsetup luksOpen /dev/sda4 fedora

Create a btrfs filesystem on the encrypted partition and copy the data back to it

    $ sudo mkfs.btrfs /dev/mapper/fedora
    $ sudo mount /dev/mapper/fedora /mnt/fedora
    $ sudo btrfs send /mnt/backup/homeBACKUP/ | sudo btrfs receive /mnt/fedora/
    $ sudo btrfs send /mnt/backup/rootBACKUP/ | sudo btrfs receive /mnt/fedora/
    $ sudo mv /mnt/fedora/rootBACKUP/ /mnt/fedora/root
    $ sudo mv /mnt/fedora/homeBACKUP/ /mnt/fedora/home
    $ sudo btrfs subvolume list /mnt/fedora
    ID 257 gen 11 top level 5 path home
    ID 258 gen 24 top level 5 path root

# Fix up references to the old filesystem

    $ sudo blkid
    /dev/disk/by-label/Fedora-WS-Live-24-1-2: UUID="2016-06-14-16-54-29-00" LABEL="Fedora-WS-Live-24-1-2" TYPE="iso9660" PTUUID="537ee902" PTTYPE="dos"
    /dev/sda1: SEC_TYPE="msdos" UUID="1616-FDDC" TYPE="vfat" PARTLABEL="EFI System Partition" PARTUUID="5738d418-52f4-4b56-af99-1f4cf05518d0"
    /dev/sda2: UUID="c6a4c58a-b13d-4f93-9841-81b0b04d35ed" TYPE="ext4" PARTUUID="8e130091-9e47-4eba-a5d1-fa4a5627fbfe"
    /dev/sda3: UUID="2d4bc346-b2f2-4436-b583-230fb1ff5dba" TYPE="swap" PARTUUID="a6376260-7fee-42b0-87be-3f4da06f6f56"
    /dev/sda4: UUID="8d0f7036-74e7-4958-aaaf-36645dc30065" TYPE="crypto_LUKS" PARTUUID="2f34589e-f169-4132-9ce2-147bc6d759ac"
    /dev/loop0: TYPE="squashfs"
    /dev/loop1: LABEL="Anaconda" UUID="9234c2e3-f613-4534-8167-1a9671619b1a" TYPE="ext4"
    /dev/loop2: TYPE="DM_snapshot_cow"
    /dev/mapper/live-rw: LABEL="Anaconda" UUID="9234c2e3-f613-4534-8167-1a9671619b1a" TYPE="ext4"
    /dev/mapper/live-base: LABEL="Anaconda" UUID="9234c2e3-f613-4534-8167-1a9671619b1a" TYPE="ext4"
    /dev/sdb1: UUID="07badae9-6502-4199-b426-35307774531e" UUID_SUB="82bfec92-ff61-4d5d-a139-b7fd84a607c8" TYPE="btrfs" PARTUUID="46b95e2b-01"
    /dev/mapper/fedora: UUID="3be747dc-7f36-4417-a475-4ef9d99e2ed0" UUID_SUB="14ca7b00-26e6-4704-a047-1ae73474d52f" TYPE="btrfs"

    $ cd /mnt/fedora/root
    $ sudo btrfs property set -ts /mnt/fedora/root ro false
    $ sudo btrfs property set -ts /mnt/fedora/home ro false
    $ sudo vi etc/fstab
    # Replace UUID in fstab with /dev/mapper/fedora UUID
    $ sudo vi etc/crypttab
    $ sudo cat etc/crypttab
    luks-8d0f7036-74e7-4958-aaaf-36645dc30065    UUID=8d0f7036-74e7-4958-aaaf-36645dc30065    none

Update kernel command line to trigger decryption:
    :::bash
    $ sudo vi /mnt/efi/EFI/fedora/grub.cfg
    # Copy first menuentry stanza, change kernelefi line to add:
    root=UUID=3be747dc-7f36-4417-a475-4ef9d99e2ed0 rd.luks.uuid=8d0f7036-74e7-4958-aaaf-36645dc30065

# Fix boot issues

If we try to boot at this point, the process will get stuck, and eventually drop us in a dracut emergency shell. Exploring, we can see that there is no cryptsetup command in this initrd. We'll need to build a new initrd that has all of the tools needed for this boot process. Here's how I got it to work, after some trial and error. There are probably ways that are simpler or more independent of what kind of livecd you have, but the following works with a F24 livecd and F23 or F24 installed system.
1. Boot livecd again
2. Find the packages for the latest kernel installed on your system on koji: https://koji.fedoraproject.org/koji/buildinfo?buildID=807875
3. Download kernel, kernel-core, and kernel-modules packages
4. Build the new initrd:
    :::bash
    $ sudo dnf install ~/Downloads/*.rpm
    $ sudo mkdir /mnt/boot /mnt/efi
    $ sudo mount /dev/sda1 /mnt/efi
    $ sudo mount /dev/sda2 /mnt/boot
    $ sudo dracut --add "crypt btrfs" --add-drivers "dm_crypt btrfs" /mnt/boot/initramfs-new 4.7.7-200.fc24.x86_64
    $ sudo vi /mnt/efi/EFI/fedora/grub.cfg  # change initrdefi line to /initramfs-new

At this point, you should be able to boot into the new system by selecting the LUKS entry from the grub menu and entering your LUKS passphrase at the prompt!


# Cleanup
The booted system can generate the files it needs more cleanly than we could from the livecd, so recreate the initrds:

    :::bash
    $ sudo dracut --regenerate-all --force
    $ sudo vim /etc/default/grub
    # add rd.luks.uuid=8d0f7036-74e7-4958-aaaf-36645dc30065 to GRUB_CMDLINE_LINUX variable
    $ sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg
    $ sudo rm /boot/initramfs-new

Reboot. All of the GRUB targets should now work correctly.

# References
[Fedora guide](https://fedoraproject.org/wiki/Disk_Encryption_User_Guide#Creating_Encrypted_Block_Devices_on_the_Installed_System_After_Installation)

[Btrfs guide from Arch](https://wiki.archlinux.org/index.php/Dm-crypt/Encrypting_an_entire_system#Btrfs_subvolumes_with_swap)
