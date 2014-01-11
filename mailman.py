# source: http://rosettacode.org/wiki/Send_an_email#Python

import smtplib

from mail_settings import *

GMAILSMTP = 'smtp.gmail.com:587'

def sendemail(to_addr_list, subject, message, smtpserver=GMAILSMTP):
    header  = 'From: %s\n' % from_addr
    header += 'To: %s\n' % ','.join(to_addr_list)
    header += 'Subject: %s\n\n' % subject
    message = header + message
 
    server = smtplib.SMTP(smtpserver)
    server.starttls()
    server.login(login,password)
    problems = server.sendmail(from_addr, to_addr_list, message)
    server.quit()
    return problems

sendemail(to_addr_list = ['a@vlabs.ac.in', 'chandan@vlabs.ac.in'],
          subject      = 'Howdy', 
          message      = 'Hi! How are you buddy. This is simo')