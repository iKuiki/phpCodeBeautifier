import sublime, sublime_plugin
import os, sys, subprocess, codecs, webbrowser

try:
    import commands
except ImportError:
    pass

PLUGIN_FOLDER = os.path.dirname(os.path.realpath(__file__))

class PhpCbCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # Load Settings
        settings = sublime.load_settings("phpcb.sublime-settings")
        # Save the current viewport position to scroll to it after formatting.
        previous_selection = list(self.view.sel()) # Copy.
        previous_position = self.view.viewport_position()

        # Save the already folded code to refold it after formatting.
        # Backup of folded code is taken instead of regions because the start and end pos
        # of folded regions will change once formatted.
        folded_regions_content = [self.view.substr(r) for r in self.view.folded_regions()]

        # Get the current text in the buffer and save it in a temporary file.
        # This allows for scratch buffers and dirty files to be linted as well.
        entire_buffer_region = sublime.Region(0, self.view.size())
        text_selection_region = self.view.sel()[0]
        is_formatting_selection_only = \
          settings.get('format_selection_only', "true") \
          and not text_selection_region.empty()

        if is_formatting_selection_only:
            temp_file_path, buffer_text = self.save_buffer_to_temp_file(text_selection_region)
        else:
            temp_file_path, buffer_text = self.save_buffer_to_temp_file(entire_buffer_region)
        output = self.phpcb(temp_file_path)
        os.remove(temp_file_path)
        output = output[0:].decode("utf-8")

        # If the prettified text length is nil, the current syntax isn't supported.
        if len(output) < 1:
            return

        # Replace the text only if it's different.
        if output != buffer_text:
            if is_formatting_selection_only:
                self.view.replace(edit, text_selection_region, output)
            else:
                self.view.replace(edit, entire_buffer_region, output)

        self.refold_folded_regions(folded_regions_content, output)
        self.view.set_viewport_position((0, 0), False)
        self.view.set_viewport_position(previous_position, False)
        self.view.sel().clear()

        # Restore the previous selection if formatting wasn't performed only for it.
        if not is_formatting_selection_only:
            for region in previous_selection:
                self.view.sel().add(region)

    def save_buffer_to_temp_file(self, region):
        buffer_text = self.view.substr(region)
        temp_file_name = ".__temp__"
        temp_file_path = PLUGIN_FOLDER + "/" + temp_file_name
        f = codecs.open(temp_file_path, mode="w", encoding="utf-8")
        f.write(buffer_text)
        f.close()
        return temp_file_path, buffer_text

    def get_phpcb_path(self):
        platform = sublime.platform()
        phpcb = sublime.load_settings("phpcb.sublime-settings").get('path', "").get(platform)
        print("Using phpCB path on '" + platform + "': " + phpcb)
        return phpcb

    def get_phpcb_option(self, cmd):
        options = sublime.load_settings("phpcb.sublime-settings").get('format_option', "")
        if options.get('space_after_if', "true"):
            cmd.insert(1,"--space-after-if")
        if options.get('space_after_switch', "true"):
            cmd.insert(1,"--space-after-switch")
        if options.get('space_after_while', "true"):
            cmd.insert(1,"--space-after-while")
        if options.get('space_before_start_angle_bracket', "true"):
            cmd.insert(1,"--space-before-start-angle-bracket")
        if options.get('space_after_end_angle_bracket', "true"):
            cmd.insert(1,"--space-after-end-angle-bracket")
        if options.get('space_after_start_bracket', "false"):
            cmd.insert(1,"--space-after-start-bracket")
        if options.get('space_before_end_bracket', "false"):
            cmd.insert(1,"--space-before-end-bracket")
        if options.get('extra_padding_for_case_statement', "true"):
            cmd.insert(1,"--extra-padding-for-case-statement")
        if options.get('glue_amperscore', "true"):
            cmd.insert(1,"--glue-amperscore")
        if options.get('change_shell_comment_to_double_slashes_comment', "true"):
            cmd.insert(1,"--change-shell-comment-to-double-slashes-comment")
        if options.get('indent_with_tab', "true"):
            cmd.insert(1,"--indent-with-tab")
        if options.get('padding_char_count'):
            if int(options.get('padding_char_count'))>0:
                cmd.insert(1,"--padding-char-count")
                cmd.insert(2,options.get('padding_char_count'))
        if options.get('force_large_php_code_tag', "true"):
            cmd.insert(1,"--force-large-php-code-tag")
        if options.get('force_true_false_null_contant_lowercase', "true"):
            cmd.insert(1,"--force-true-false-null-contant-lowercase")
        if options.get('comment_rendering_style'):
            cmd.insert(1,"--comment-rendering-style")
            cmd.insert(2,options.get('comment_rendering_style'))
        if options.get('align_equal_statements', "false"):
            cmd.insert(1,"--align-equal-statements")
        if options.get('optimize_eol', "true"):
            cmd.insert(1,"--optimize-eol")
        if options.get('one_true_brace_function_declaration', "false"):
            cmd.insert(1,"--one-true-brace-function-declaration")
        return cmd


    def phpcb(self, temp_file_path):
        try:
            phpcb_path = self.get_phpcb_path()
            cmd = [phpcb_path, temp_file_path]
            cmd = self.get_phpcb_option(cmd)
            output = self.get_output(cmd)

            return output

        except:
            # Something bad happened.
            print("Unexpected error({0}): {1}".format(sys.exc_info()[0], sys.exc_info()[1]))

            # Usually, it's just node.js not being found. Try to alleviate the issue.
            msg = "phpCB was not found in the default path. Please specify the location."
            sublime.error_message(msg)

    def get_output(self, cmd):
        if int(sublime.version()) < 3000:
            if sublime.platform() != "windows":
                # Handle Linux and OS X in Python 2.
                run = '"' + '" "'.join(cmd) + '"'
                return commands.getoutput(run)
            else:
                # Handle Windows in Python 2.
                # Prevent console window from showing.
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                return subprocess.Popen(cmd, \
                    stdout=subprocess.PIPE, \
                    startupinfo=startupinfo).communicate()[0]
        else:
            # Handle all OS in Python 3.
            run = '"' + '" "'.join(cmd) + '"'
            print("run is:"+run)
            return subprocess.check_output(run, stderr=subprocess.STDOUT, shell=True, env=os.environ)

    def refold_folded_regions(self, folded_regions_content, entire_file_contents):
        self.view.unfold(sublime.Region(0, len(entire_file_contents)))
        region_end = 0

        for content in folded_regions_content:
            region_start = entire_file_contents.index(content, region_end)
            if region_start > -1:
                region_end = region_start + len(content)
                self.view.fold(sublime.Region(region_start, region_end))

class PhpCbEventListeners(sublime_plugin.EventListener):
    @staticmethod
    def on_pre_save(view):
        if sublime.load_settings("phpcb.sublime-settings").get('on_save', "false"):
            view.run_command('php_cb')
    def on_load(self, view):
        if sublime.load_settings("phpcb.sublime-settings").get('on_load', "false"):
            view.run_command('php_cb')