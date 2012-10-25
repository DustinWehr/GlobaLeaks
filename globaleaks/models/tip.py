# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from storm.twisted.transact import transact
from storm.locals import Int, Pickle, Date, Unicode, RawStr, Bool
from storm.locals import Reference, ReferenceSet

# under the voce of "needlessy overcomplications", Twister + Storm
# http://twistedmatrix.com/users/radix/storm-api/storm.store.ResultSet.html
from globaleaks.utils import idops, log

from globaleaks.models.base import TXModel, ModelError
from globaleaks.models.receiver import Receiver
from globaleaks.models.admin import Context

from globaleaks.messages.responses import errorMessage

__all__ = [ 'InternalTip', 'Folder', 'File', 'Comment',
            'ReceiverTip', 'PublicStats', 'WhistleblowerTip' ]

class TipModelError(ModelError):
    log.debug("[D] %s %s " % (__file__, __name__), "Class TipModelError", "ModelError", ModelError)
    pass

class TipNotFoundError(TipModelError):
    log.debug("[D] %s %s " % (__file__, __name__), "Class TipNotFoundError", "TipModelError", TipModelError)
    pass

class Folder(TXModel):
    """
    This represents a file set: a collection of files, description, time
    Every receiver has a different Folder, and if more folder exists, the
    number of folder is (R * Folder_N).
    This is the unique way we had to ensure end to end encryption WB-receiver,
    and if uncrypted situation, simply the Files referenced here are also
    referenced in the other Folders.
    """
    log.debug("[D] %s %s " % (__file__, __name__), "Folder", "TXModel", TXModel)
    __storm_table__ = 'folders'

    folder_gus = Unicode(primary=True)

    name = Unicode()
    description = Unicode()

    property_applied = Pickle()
    # actually there are not property, but here would be marked if symmetric
    # asymmetric encryption has been used.

    upload_time = Date()

    # to be expanded in the near future XXX
    # at the moment, folder is not associated to a receiver
    #  associated_receiver_id = Int()
    #  associated_receiver = Reference(associated_receiver_id, Receiver.id)
    # associated_receiver_id is useful for show, in the general page of the
    # receiver, eventually the latest available folders

    internaltip_id = Int()
    # internaltip = Reference(internaltip_id, InternalTip.id)
    # GLBackend/globaleaks/models/tip.py", line 67, in Folder
    # internaltip = Reference(internaltip_id, InternalTip.id)
    # NameError: name 'InternalTip' is not defined
    # -- then, I moved that line after InternalTip


def file_dicts(self):
        file_dicts = []
        log.debug("Processing %s" % self.files)
        for f in self.files:
            log.debug("Generating file dict")
            print "In here y0 %s" % f
            file_dict = {'name': f.name,
                    'description': f.description,
                    'size': f.size,
                    'content_type': f.content_type,
                    'date': f.uploaded_date,
                    'metadata_cleaned': f.metadata_cleaned,
                    'completed': f.completed}
            log.debug("Done %s" % file_dict)
            file_dicts.append(file_dict)
        return file_dicts


class File(TXModel):
    """
    The file are *stored* here, along with their properties
    """
    log.debug("[D] %s %s " % (__file__, __name__), "File", "TXModel", TXModel)
    __storm_table__ = 'files'

    file_gus = Unicode(primary=True)

    name = Unicode()
    content = RawStr()

    completed = Bool()

    shasum = RawStr()

    description = Unicode()
    content_type = Unicode()

    size = Int()

    metadata_cleaned = Bool()
    uploaded_date = Date()

    folder_gus = Unicode()
    folder = Reference(folder_gus, Folder.folder_gus)

Folder.files = ReferenceSet(Folder.folder_gus, File.folder_gus)

class Comment(TXModel):
    log.debug("[D] %s %s " % (__file__, __name__), "Comment", "TXModel", TXModel)
    __storm_table__ = 'comments'

    id = Int(primary=True)

    type = Unicode()
    content = Unicode()
    author = Unicode()
    comment_date = Date()

    internaltip_id = Int()
    # internaltip = Reference(internaltip_id, InternalTip.id)
    # GLBackend/globaleaks/models/tip.py", line 133, in Comment
    # internaltip = Reference(internaltip_id, InternalTip.id)
    # NameError: name 'InternalTip' is not defined
    # -- then, I moved that line after InternalTip decl


class InternalTip(TXModel):
    """
    This is the internal representation of a Tip that has been submitted to the
    GlobaLeaks node.
    It has a one-to-many association with the individual Tips of every receiver
    and whistleblower.

    Every tip has a certain shared data between all, and they are here collected, and
    this StoredTip.id is referenced by Folders, Files, Comments, and the derived Tips
    """
    log.debug("[D] %s %s " % (__file__, __name__), "InternalTip", "TXModel", TXModel)
    __storm_table__ = 'internaltips'

    # an InternalTip has not a _gus, then is used classic id = Int()
    id = Int(primary=True)
    fields = Pickle()

    pertinence_value = Int()
    escalation_threshold = Int()

    comments = Pickle()
    pertinence = Int()

    creation_date = Date()
    expiration_date = Date()

    downloads = Int()

    # the LIMITS are defined and declared *here*, and then
    # in the (Special|Receiver)Tip there are the view_count
    # in Folders(every Receiver has 1 to N folders), has the download_count
    access_limit = Int()
    download_limit = Int()

    folders = ReferenceSet(id, Folder.internaltip_id)
        # remind: I've removed file reference from InternalTip
        # because do not exists file leaved alone
    comments = ReferenceSet(id, Comment.internaltip_id)

    context_gus = Unicode()
    context = Reference(context_gus, Context.context_gus)

    def folder_dicts(self):
        log.debug("[D] %s %s " % (__file__, __name__), "InternalTip", "folder_dicts")
        folder_dicts = []
        for folder in self.folders:
            folder_dict = {'name': folder.name,
                    'description': folder.description,
                    'downloads': self.downloads,
                    'files': folder.file_dicts()}
            folder_dicts.append(folder_dict)
        return folder_dicts

    def postpone_expiration(self):
        """
        function called when a receiver has this option
        """
        log.debug("[D] %s %s " % (__file__, __name__), "InternalTip", "postpone_expiration")

    def tip_total_delete(self):
        """
        function called when a receiver choose to remove a submission
        and all the derived tips. is called by scheduler when
        timeoftheday is >= expired_date
        """
        log.debug("[D] %s %s " % (__file__, __name__), "InternalTip", "tip_total_delete")

Folder.internaltip = Reference(Folder.internaltip_id, InternalTip.id)
Comment.internaltip = Reference(Comment.internaltip_id, InternalTip.id)

class Tip(TXModel):
    log.debug("[D] %s %s " % (__file__, __name__), "Class Tip", "TXModel", TXModel)
    __storm_table__ = 'tips'

    # remind: the previous name of this variable was 'address'
    tip_gus = Unicode(primary=True)

    type = Unicode()
    password = Unicode()

    internaltip_id = Int()
    internaltip = Reference(internaltip_id, InternalTip.id)

    def get_sub_index(self):
        log.debug("[D] %s %s " % (__file__, __name__), "Class Tip", "get_sub_index")
        ret = {
        #"notification_adopted": unicode,
        #"delivery_adopted": unicode,
        "download_limit": self.internaltip.download_limit,
        # remind: download_performed is inside the folderDict
        "access_limit": self.internaltip.access_limit,
        #"access_performed": self.,
        "expiration_date": self.internaltip.expiration_date,
        "creation_date": self.internaltip.creation_date,
        #"last_update_date": self.internaltip.last_update_date,
        "comment_number": len(list(self.internaltip.comments)),
        "folder_number": len(list(self.internaltip.folders)),
        "overall_pertinence": self.internaltip.pertinence
        }
        return ret

    @transact
    def lookup(self, receipt):
        """
        receipt actually is either a random_tip_gus and a random_receipt_gus,
        in the future, would be the hash of a random_receipt_gus.
        """
        log.debug("[D] %s %s " % (__file__, __name__), "Class Tip", "lookup", "receipt", receipt )
        store = self.getStore('lookup')

        tip = store.find(Tip, Tip.tip_gus == receipt).one()
        if not tip:
            store.rollback()
            store.close()
            raise TipNotFoundError

        tip_sub_index = tip.get_sub_index()

        folders = tip.internaltip.folders
        # ANSWERED folders do not exist in the Tip variables, why ?
        # + folders shall not be downloaded by the WB, this info can be stripped
        # off the folder_gus (required to download)
        #
        # As mentioned on IRC for the moment we want to keep it simple and not
        # have a folder per receiver.
        # Once we will have the functionality to add the settings that
        # distinguish the folders based on the receiver we will change the
        # folders here to do a lookup on folders for the tip that is specific
        # to this receiver

        comments = tip.internaltip.comments
        # ANSWERED comments do not exist in the Tip variables, why ?
        # They are not properties of the Tip variable, but of the internal tip.
        # The comments are currently global to every tip.

        context = tip.internaltip.context_gus

        receiver_dicts = tip.internaltip.context.receiver_dicts()
        folders = tip.internaltip.folder_dicts()

        tip_details = {'tip': tip_sub_index,
                   'fields': tip.internaltip.fields,
                   'folders': folders,#folders,
                   'comments': None, #comments,
                   'context': context,
                   'receivers': receiver_dicts
        }
        store.commit()
        store.close()

        return tip_details


class ReceiverTip(Tip):
    """
    This is the table keeping track of ALL the receivers activities and
    date in a Tip, Tip core data are stored in StoredTip. The data here
    provide accountability of Receiver accesses, operations, options.
    """
    notification_date = Date()
    authoptions = Pickle()
    # remind: here we can make a password checks, PersonalPreference has a
    # stored hash of the actual password. when Receiver change a password, do not change
    # in explicit way also the single Tips password.

    # all this four details need to be properly moved/renamed
    total_view_count = Int()
    total_download_count = Int()
    relative_view_count = Int()
    relative_download_count = Int()

    last_access = Date()
    pertinence_vote = Int()

    receiver_gus = Unicode()
    receiver = Reference(receiver_gus, Receiver.receiver_gus)

    def new(self, receiver_gus):
        log.debug("[D] %s %s " % (__file__, __name__), "Class ReceiverTip", "new", "receiver_id", receiver_gus )
        log.debug("Creating receiver tip for %s" % receiver_gus)

        # all this four details need to be properly moved/renamed
        self.total_view_count = 0
        self.total_download_count = 0
        self.relative_view_count = 0
        self.relative_download_count = 0
        self.receiver_gus = receiver_gus

        self.authoptions = {}

        self.tip_gus = idops.random_tip_gus()

        self.type = u'receiver'
        log.debug("Created tip", self.tip_gus, "for", receiver_gus)

    @transact
    def receiver_dicts(self):
        log.debug("[D] %s %s " % (__file__, __name__), "Class ReceiverTip", "receiver_dicts" )
        store = self.getStore('receiver_dicts')

        receiver_dicts = []

        for receiver in store.find(Receiver):
            receiver_dict = {}
            receiver_dict['gus'] = receiver.receiver_gus
            receiver_dict['name'] = receiver.name
            receiver_dict['description'] = receiver.receiver_description

            receiver_dict['can_delete_submission'] = receiver.can_delete_submission
            receiver_dict['can_postpone_expiration'] = receiver.can_postpone_expiration
            receiver_dict['can_configure_delivery'] = receiver.can_configure_delivery

            receiver_dict['can_configure_notification'] = receiver.can_configure_notification
            receiver_dict['can_trigger_escalation'] = receiver.can_trigger_escalation

            receiver_dict['languages_supported'] = receiver.languages_supported
            receiver_dicts.append(receiver_dict)

        store.commit()
        store.close()

        return receiver_dicts

    @transact
    def add_comment(self, tip_gus, comment):
        """
        From a Tip hook the internalTip, and update comments inside.
        comment_type and name of the author need to be written at the commit
        time, and not when comments are show to the users (perhaps, some user would
        remove a tip, breaking reference. this separation it's required for that).
        comment_type of those comments is "receiver" (other are "whistleblower" and
        "system")
        """
        log.debug("[D] %s %s " % (__file__, __name__), "ReceiverTip class", "add_comment", "tip_gus", tip_gus, "comment", comment)
        store = self.getStore('add_comment')

        try:
            # XXX - aarrgghh - naming refactor remind!
            tip = store.find(ReceiverTip, ReceiverTip.tip_gus == tip_gus).one()
        except NotOneError, e:
            log.err("add_comment (receiver side): Problem looking up %s" % tip_gus)
            store.rollback()
            store.close()
            raise TipNotFoundError

        if not tip:
            store.rollback()
            store.close()
            raise TipNotFoundError

        newcomment = Comment()
        newcomment.internaltip_id = tip.internaltip.id
        newcomment.type = u"receiver" # XXX its commentENUM
        newcomment.content = comment

        print "debug 1", type(tip.receiver)
        print "debug 2", type(tip.receiver_gus)
        newcomment.author = u'temp fake name'

        store.add(newcomment)
        store.commit()
        store.close()


class WhistleblowerTip(Tip):
    """
    WhisteleblowerTip is intended, at the moment, to provide a whistleblower access to the Tip.
    differently from the ReceiverTips, has a secret and/or authentication checks, has
    different capabilities, like: cannot not download, cannot express pertinence, and
    other operation permitted to the WB shall be configured by the Admin.

    SpecialTip contains some information, but the tip data returned to the WB, is
    composed by SpecialTip + Tip
    """

    """
    need to have a tip_US (unique string) ? may even not, in fact, in the 0.1 release
    we had used a tip_US just because was stored in the same table, but if we support
    a more complex auth system for the whistleblower, we want that WB come back
    to the tip only using this method, not using /tip/<t_US> like a receiver.

    This is the reason because here is not placed a t_US, but just a secret
    """
    log.debug("[D] %s %s " % (__file__, __name__), "Class WhistleblowerTip")
    secret = Pickle()

    # XXX we probably don't want to store this stuff for the WB receipt.
    #     we may just want to store the last_access count, but properly
    #     anonymize it, like only store the fact that they logged in in the
    #     last week. So store just a week number.
    #view_count = Int()
    #last_access = Date()


class PublicStats(TXModel):
    """
    * Follow the same logic of admin.AdminStats,
    * need to be organized along with the information that we want to shared to the WBs:
       *  active_submission represent the amount of submission active in the moment
       *  node activities is a sum of admin + receiver operation
    * that's all time dependent information
       * remind: maybe also non-time dependent information would exists, if a node want to publish also their own analyzed submission, (but this would require another db table)
    """
    log.debug("[D] %s %s " % (__file__, __name__), "Class PublicStats")
    __storm_table__ = 'publicstats'

    createQuery = "CREATE TABLE " + __storm_table__ +\
                   "(id INTEGER PRIMARY KEY, active_submissions INT, node_activities INT, uptime INT"

    id = Int(primary=True)

    active_submissions = Int()
    node_activities = Int()
    uptime = Int()
    """
    likely would be expanded, but avoiding to spread information that may lead an attacker advantaged
    """


"""
The classic tip stay in receiver.ReceiverTip
"""
