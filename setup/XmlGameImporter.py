# -*- coding: utf-8 -*-
'''
Created on Aug 26, 2013

@author lavalamp

    Copyright 2012 Root the Box

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
------------------------------------------------------------------------------

'''

from uuid import uuid4
from shutil import copyfile
from os import path, _exit, listdir
from sqlalchemy.exc import OperationalError, IntegrityError, ProgrammingError
import sys
import defusedxml.cElementTree as ET
from libs.ConsoleColors import *
from models import dbsession, Sponsor, Corporation,\
    Flag, Box, BoxResource

def print_info(information):
    print(INFO+"Info: " + information)

def print_success(success):
    print(INFO+"Success: " + success)

def print_warning_and_exit(warning):
    print(WARN+"Error: " + warning)
    _exit(1)

def validate_xml_node_children(xmlnode, children, nodename):
    errors = []
    
    for curchild in children:
        if xmlnode.find(curchild) is None:
            errors.append("The node '" + nodename + "' is expected to have a child of type '" + curchild + "'.")
    
    return errors

def validate_xml_box_file_old(filepath):
    errors = []
    
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        #TODO make sure box has a unique name
        
        # Root node must be of type 'box' and have exactly 7 children
        if root.tag != 'box':
            errors.append("Root node must be of type 'box'.")
        if len(root) is not 7:
            errors.append("The root node must have precisely seven children.")
            
        # Make sure the root children are of the correct type
        expected_children = ['sponsor', 'corporation', 'name', 'difficulty', 'avatar', 'description', 'flags']
        errors += validate_xml_node_children(root, expected_children, 'box')
         
        # Validate the sponsor child
        sponsor = root.find('sponsor')
        
        # Sponsors should have exactly 4 children
        if len(sponsor) is not 4:
            errors.append("The sponsor node is expected to have precisely four children.")
        
        # Make sure the sponsor children are of the correct type
        expected_children = ['name', 'description', 'url', 'logo']
        errors += validate_xml_node_children(sponsor, expected_children, 'sponsor')
        
        #TODO validate the values for all the nodes within the sponsor node
        
        # Validate the corporation child
        corporation = root.find('corporation')
        
        # Corporations should have exactly 2 children
        if len(corporation) is not 2:
            errors.append("The corporation node is expected to have precisely two children.")
            
        # Make sure the corporation children are of the correct type
        expected_children = ['name', 'description']
        errors += validate_xml_node_children(corporation, expected_children, 'corporation')
        
        #TODO validate all the values within the corporation node children
        
        # Validate the box name
        #TODO validate this
        
        # Validate the box difficulty
        #TODO validate this
        
        # Validate the box avatar
        #TODO validate this
        
        # Validate the box description
        #TODO validate this
        
        # Validate the box flags
        flags = root.find('flags')
        for ind, curflag in enumerate(flags):
            
            # Make sure the node is of the proper type
            if curflag.tag != 'flag':
                errors.append("The " + str(ind) + " child of the flags node was not of the proper type ('flag').")
                
            # Flags are expected to have precisely 4 children
            if len(curflag) is not 4:
                errors.append("Flag nodes are expected to have precisely four children")
                
            # Make sure the node children are of the expected node types
            expected_children = ['name', 'token', 'description', 'value']
            errors += validate_xml_node_children(curflag, expected_children, 'flag_'+str(ind))
            
            #TODO validate all of the values within each flag's children
    except ET.ParseError as e:
        errors.append("ParseError thrown: " + str(e))
    
    return errors

def move_image_file_and_get_name(filepath):
    #TODO move this to a configuration file
    targetdir = path.abspath('files/avatars/')
    p, ext = path.splitext(filepath)
    uuid = unicode(uuid4())
    
    #print "Old filepath is " + filepath
    #print "New filepath is " + targetdir + '/' + uuid + ext

    try:
        copyfile(filepath, targetdir + '/' + uuid + ext)
    except IOError as e:
        print_warning_and_exit("IOError thrown while moving image file: " + str(e))
    
    return uuid + ext    
    
#TODO don't use hard-coded game directory, allow for configuration elsewhere
def import_xml_box_files_for_game(game_name, input_game_level_id):
    game_dir = path.abspath('games/' + game_name)
    for curfile in listdir(game_dir):
        if curfile.endswith('.xml'):
            import_xml_box_file(game_dir + '/' + curfile, input_game_level_id)

#TODO implement IP address
def import_xml_box_file(filepath, input_game_level_id):
    
    print_info("Starting import of file " + filepath)
    
    #TODO refactor validation to reflect new XML format
    #errors = validate_xml_box_file(filepath)
    errors = []
    if len(errors) > 0:
        for ind, error in enumerate(errors):
            print WARN+"Error " + str(ind) + ": " + error
        print_warning_and_exit("XML file was not valid.")
    
    try:
        tree = ET.parse(filepath)
        boxnode = tree.getroot()
        filedir = path.dirname(filepath)
        
        # Check to see if box already exists
        bname = boxnode.find('name').text
        if len(Box.by_name(unicode(bname))) is not 0:
            print_info("Box with name '" + bname + "' already exists. Continuing to next file...")
            return
        
        # If box does not already exist, then check for corporation existing
        corpnode = boxnode.find('corporation')
        corpname = corpnode.find('name').text
        corp = Corporation.by_name(unicode(corpname))
        if corp is not None:
            print_info("Corporation with name '" + corpname + "' already exists. Using the pre-existing corporation.")
        else:
            # If corporation does not exist, then we must create it
            print_info("Corporation does not exist. Creating now.")
            corpdesc = corpnode.find('description').text
            corp = Corporation(
                name=unicode(corpname),
                description=unicode(corpdesc)
            )
            dbsession.add(corp)
            dbsession.flush()
            print_info("Corporation with name '" + corpname + "' successfully created.")
            
        # Check if the box is sponsored
        sponsornode = boxnode.find('sponsor')
        spon = None
        if sponsornode is None:
            print_info("The box does not appear to have a sponsor.")
        else:
            # The box is sponsored.
            print_info("The box has a sponsor")
            sname = sponsornode.find('name').text
            
            # Check to see if the sponsor already exists in the DB
            spon = Sponsor.by_name(unicode(sname))
            if spon is not None:
                print_info("The sponsor with name '" + sname + "' already exists in the DB. Using the pre-existing sponsor.")
            else:
                print_info("The sponsor does not yet exist.")
                sdesc = sponsornode.find('description').text
                surl = sponsornode.find('url').text
                slogo = sponsornode.find('logo').text
                
                # Move the sponsor's logo
                slogomoved = move_image_file_and_get_name(filedir + '/' + slogo) 
                
                spon = Sponsor(
                    name=unicode(sname),
                    logo=unicode(slogomoved),
                    description=unicode(sdesc),
                    url=unicode(surl)
                )
                
                dbsession.add(spon)
                dbsession.flush()
                print_info("Sponsor with name '" + sname + "' successfully created.")
        
        # Now that we have the corporation and potentially the sponsor, create the box
        bdiff = boxnode.find('difficulty').text
        bavatar = boxnode.find('avatar').text
        bdesc = boxnode.find('description').text
        
        # Move the box's avatar
        bavatarmoved = move_image_file_and_get_name(filedir + '/' + bavatar)
            
        box = Box(
            name=unicode(bname),
            corporation_id=corp.id,
            difficulty=unicode(bdiff),
            game_level_id=input_game_level_id,
            _description=unicode(bdesc),
            avatar=unicode(bavatarmoved),
            sponsor_id=spon.id
        )
        
        dbsession.add(box)
        dbsession.flush()
        
        print_info("Box with name '" + bname + "' successfully created.")
        
        # Now find and create the flags from the file
        print_info("Now processing flags for box.")
        flagsnode = boxnode.find('flags')
        for curflagnode in flagsnode:
            curflagname = curflagnode.find('name').text
            curflagtoken = curflagnode.find('token').text
            curflagdesc = curflagnode.find('description').text
            curflagvalue = curflagnode.find('value').text
            newflag = Flag(
                name=unicode(curflagname),
                token=unicode(curflagtoken),
                is_file=False, #TODO implement file upload stuff
                description=unicode(curflagdesc),
                value=abs(int(curflagvalue)),
                box_id=box.id
            )
            dbsession.add(newflag)
            dbsession.flush()
            print_info("Flag with name '" + curflagname + "' successfully created.")
            
        # Now check to see if there are any box resources for this box
        resourcesnode = boxnode.find('resources')
        if resourcesnode is not None:
            print_info("Box appears to have related resources.")
            for resourcenode in resourcesnode:
                rurl = resourcenode.find('url').text
                rtag = resourcenode.find('tag').text
                rdesc = resourcenode.find('description').text
                res = BoxResource(
                    url=unicode(rurl),
                    tag=unicode(rtag),
                    description=unicode(rdesc),
                    box_id=box.id
                )
                dbsession.add(res)
                dbsession.flush()
                print_info("BoxResource with tag of '" + rtag + "' successfully created.")
        
        # And we're done!
        print_info("Box with name '" + bname + "' successfully created!")
        
    except ProgrammingError as e:
        print "ProgrammingError thrown: " + str(e)
    except IntegrityError as e:
        print "IntegrityError thrown: " + str(e)
    except OperationalError as e:
        print "OperationalError thrown: " + str(e)
    except ET.ParseError as e:
        print "ParseError thrown: " + str(e)
    except:
        print_warning_and_exit("Unexpected error:" + str(sys.exc_info()[0]))

def import_xml_box_file_old(filepath, input_game_level_id):
    
    print_info("Starting import of file " + filepath)
    
    errors = validate_xml_box_file(filepath)
    if len(errors) > 0:
        for ind, error in enumerate(errors):
            print WARN+"Error " + str(ind) + ": " + error
        print_warning_and_exit("XML file was not valid.")

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        filedir = path.dirname(filepath)
            
        # Get information for sponsor
        sponsornode = root[0]
        sname = sponsornode.find('name').text
        
        # Check to see if this sponsor already exists
        exists = Sponsor.by_name(unicode(sname))
        
        # If sponsor already exists then move on to processing other parts of the file
        if exists is not None:
            spon = exists
        else:
            sdesc = sponsornode.find('description').text
            surl = sponsornode.find('url').text
            slogo = sponsornode.find('logo').text
            
            # Move the logo image file and set the new logo name
            
            newslogo = move_image_file_and_get_name(filedir + '/' + slogo) 
            
            # Create the sponsor object and add it to the dbobject list
            #TODO check if sponsor already exists
            spon = Sponsor(
                name=unicode(sname),
                logo=unicode(newslogo),
                description=unicode(sdesc),
                url=unicode(surl)
            )
            
            # Add the sponsor to the DB
            dbsession.add(spon)
            dbsession.flush()
        
        # Get the corporation information
        corpnode = root[1]
        corpname = corpnode.find('name').text
        
        # Check to see if the corporation already exists
        exists = Corporation.by_name(unicode(corpname))
        
        # If corporation already exist then move on to processing other parts of the file
        if exists is not None:
            corp = exists
        else:
            corpdesc = corpnode.find('description').text
            
            # Create the corporation object and add it to the dbobject list
            corp = Corporation(
                name=unicode(corpname),
                description=unicode(corpdesc)
            )
                
            # Add the corporation to the DB
            dbsession.add(corp)
            dbsession.flush()
            
        # Get box's name
        boxname = root[2].text
        
        # Get box's difficulty
        boxdiff = root[3].text
        
        # Get box's avatar file
        boxavatarorig = root[4].text
        
        # Move the avatar file and get the new name
        boxavatar = move_image_file_and_get_name(filedir + '/' + boxavatarorig)
        
        # Get the box's description
        boxdesc = root[5].text
        
        # Create the box
        newbox = Box(
            name=unicode(boxname),
            corporation_id=corp.id,
            difficulty=unicode(boxdiff),
            game_level_id=input_game_level_id,
            _description=unicode(boxdesc),
            avatar=unicode(boxavatar),
            sponsor_id=spon.id
        )
        
        # Add the box to the DB
        dbsession.add(newbox)
        dbsession.flush()
        
        # Iterate through flags
        flags = []
        for curflagnode in root[6]:
            curflagname = curflagnode.find('name').text
            curflagtoken = curflagnode.find('token').text
            curflagdesc = curflagnode.find('description').text
            curflagvalue = curflagnode.find('value').text
            newflag = Flag(
                name=unicode(curflagname),
                token=unicode(curflagtoken),
                is_file=False, #TODO implement file upload stuff
                description=unicode(curflagdesc),
                value=abs(int(curflagvalue)),
                box_id=newbox.id
            )
            flags.append(newflag)
            
        # Add all the flags to the database
        for curflag in flags:
            dbsession.add(curflag)
        dbsession.flush()
        
        # Notify user that import has succeeded
        print_success("Import of file " + filepath + " finished without issue.")
    except ProgrammingError as e:
        print "ProgrammingError thrown: " + str(e)
    except IntegrityError as e:
        print "IntegrityError thrown: " + str(e)
    except OperationalError as e:
        print "OperationalError thrown: " + str(e)
    except ET.ParseError as e:
        print "ParseError thrown: " + str(e)
    except:
        print_warning_and_exit("Unexpected error:" + str(sys.exc_info()[0]))