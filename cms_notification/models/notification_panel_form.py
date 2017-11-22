# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openerp import models, _
from openerp.addons.cms_form.utils import string_to_bool


class CMSNotificationPanel(models.AbstractModel):
    """Hold users notifications settings."""
    _name = 'cms.notification.panel.form'
    _inherit = 'cms.form'
    _description = 'CMS notification control panel'

    _form_model = 'res.partner'
    _form_model_fields = (
        'notify_email',
        'notify_frequency',
    )
    _form_sub_fields = {
        'notify_email': {
            'digest': ('notify_frequency', ),
        }
    }

    @property
    def form_title(self):
        return _('Notification settings.')

    @property
    def form_description(self):
        return ''

    @property
    def form_msg_success_updated(self):
        return _('Changes applied.')

    def form_next_url(self, main_object=None):
        return '/my/settings/notifications'

    @property
    def form_widgets(self):
        return {
            'notify_email': 'cms.form.widget.notif_radio',
        }

    @property
    def _super(self):
        return super(CMSNotificationPanel, self)

    def _form_master_slave_info(self):
        info = self._super._form_master_slave_info()
        info.update({
            'notify_email': {
                'readonly': {
                    'notify_frequency': ('always', 'none', ),
                },
                'no_readonly': {
                    'notify_frequency': ('digest', ),
                },
                'required': {
                    'notify_frequency': ('digest', ),
                },
                'no_required': {
                    'notify_frequency': ('always', 'none', ),
                },
            },
        })
        return info

    # CMS form does not support o2m fields in an advanced way
    # so we cannot add/remove/edit `notify_conf_ids` easily.
    # Furthermore, we want to automatically show just checkboxes
    # to enable/disable subtypes in an handy way.
    # Hence, you are supposed to add a boolean field + a mapping
    # field:subtype that allows to enable/disable it on the partner.
    # The following methods take care of this.

    @property
    def _form_subtype_fields(self):
        """Return mapping from boolean form field to subtype xmlid."""
        return {
            # 'boolean_field_name': 'subtype_xmlid',
        }

    def form_get_loader(self, fname, field,
                        main_object=None, value=None, **req_values):
        """Override to provide automatic loader for boolean fields."""
        loader = self._super.form_get_loader(
            fname, field, main_object=main_object,
            value=value, **req_values
        )
        if fname in self._form_subtype_fields.keys():
            loader = self._form_load_subtype_conf_loader
        return loader

    def _form_load_subtype_conf_loader(
            self, fname, field, value, **req_values):
        """Automatically load value for subtype conf fields."""
        if fname in req_values:
            value = string_to_bool(req_values.get(fname))
        else:
            subtype = self.env.ref(self._form_subtype_fields[fname])
            explicitly_enabled = \
                subtype in self.main_object.enabled_notify_subtype_ids
            explicitly_disabled = \
                subtype in self.main_object.disabled_notify_subtype_ids
            # mail_digest machinery will send you emails in this 2 cases:
            # * you've enabled notification explicitly
            # * you have no specific settings for the subtype
            # (hence you did not disabled it)
            value = explicitly_enabled or not explicitly_disabled

        return value

    def form_after_create_or_update(self, values, extra_values):
        """Update subtype configuration for `_form_subtype_fields`."""
        self._super.form_after_create_or_update(values, extra_values)
        for fname, subtype_xmlid in self._form_subtype_fields.iteritems():
            value = extra_values.get(fname)
            subtype = self.env.ref(subtype_xmlid)
            # use sudo as we don't know if the user
            # has been allowed to update its own partner
            # and sincerely, we don't care in this case.
            self.main_object.sudo()._notify_update_subtype(subtype, value)