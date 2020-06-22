Title: Building a Custom Bootable USB to Install Debian over SSH
Category: system administration
Tags: Debian

[TOC]

# Introduction

I recently got a Soekris net6501 box that I wanted to configure as a
wireless/wired router. However, the box has no mouse/keyboard or monitor
connections, only a serial console, and I don't have the right cable. (I know,
surely everybody has RS232 gear lying around, right?) So while I'm waiting for
my null modem adapter to arrive, let's make a Debian installer USB stick that
will start up a network console automatically, so that I can SSH in and see
what I'm doing.

My method is based on
[this article](https://www.christiansaga.de/sowhatisthesolution/2016/03/13/headless-debian-install-via-ssh.html),
but it is tested on Debian 10, and simpler as we can edit the files on the USB
directly rather than re-packing the ISO.

# Steps

1. Download the [hd-media/boot.img.gz](http://ftp.us.debian.org/debian/dists/buster/main/installer-amd64/current/images/hd-media/boot.img.gz) file from a Debian mirror. This is a simple, single-partition, bootable installer image.
2. Copy the image to your USB drive: `zcat boot.img.gz > /dev/sdb`
3. Mount the USB drive: `mkdir usb; mount /dev/sdb usb; cd usb
4. Copy in a cd image: `wget https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-10.4.0-amd64-netinst.iso`
5. Edit the boot parameters in drk.cfg:
    * remove `--- quiet`
    * add `file=/hd-media/preseed.cfg auto=true`
6. Comment out the `default` line in `syslinux.cfg` so that it will fall through to the text-based configurations
7. Download the preseed template: `wget -O preseed.cfg http://www.debian.org/releases/stable/example-preseed.txt`
8. Configure the hostname and enable the network console in the preseed file:

        :::diff
        --- example-preseed.txt 2020-01-12 10:42:06.000000000 -0500
        +++ preseed.cfg     2020-05-30 08:59:49.570798811 -0400
        @@ -65,8 +65,8 @@
         # Any hostname and domain names assigned from dhcp take precedence over
         # values set here. However, setting the values still prevents the questions
         # from being shown, even if values come from dhcp.
        -d-i netcfg/get_hostname string unassigned-hostname
        -d-i netcfg/get_domain string unassigned-domain
        +d-i netcfg/get_hostname string router
        +d-i netcfg/get_domain string example.com
        
         # If you want to force a hostname, regardless of what either the DHCP
         # server returns or what the reverse DNS entry for the IP is, uncomment
        @@ -87,10 +87,10 @@
         # Use the following settings if you wish to make use of the network-console
         # component for remote installation over SSH. This only makes sense if you
         # intend to perform the remainder of the installation manually.
        -#d-i anna/choose_modules string network-console
        +d-i anna/choose_modules string network-console
         #d-i network-console/authorized_keys_url string http://10.0.0.1/openssh-key
        -#d-i network-console/password password r00tme
        -#d-i network-console/password-again password r00tme
        +d-i network-console/password password install
        +d-i network-console/password-again password install
        
         ### Mirror settings
         # If you select ftp, the mirror/country string does not need to be set.

9. Unmount the USB drive and insert it into the device you want to install.

# Does it work?
Kind of. If I booted up my Soekris box with the USB drive as the only connected
disk, it booted up into my Debian installer and started up the network console
just fine. I could SSH in and continue the installation. However, with only the
USB drive connected there was nowhere to install to. On the other hand, if I
put the internal mSATA disk back in, the box would boot from that instead and
I'd be stuck. Inserting the mSATA disk after Debian installer was booted didn't
work either. It just caused the device to become nonresponsive - I think the
mSATA controller might not support hotplugging. So, it seems like this
installer USB works, but I'm still going to need a serial cable to install my
router.
