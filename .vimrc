""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => This should be at the top
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

set nocompatible
filetype off
"
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Vundle
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()

Plugin 'VundleVim/Vundle.vim'
Plugin 'tpope/vim-fugitive'
Plugin 'ervandew/supertab'
Plugin 'Valloric/YouCompleteMe'
Plugin 'vim-syntastic/syntastic'
Plugin 'ctrlpvim/ctrlp.vim'

Plugin 'SirVer/ultisnips'

" Optional:
Plugin 'honza/vim-snippets'

call vundle#end()
filetype plugin indent on

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Backup settings
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

set backupdir=~/.vim/backup
set directory=~/.vim/tmp
set history=4096
set undolevels=1024
set viminfo='100,<1000,s100,h
set viminfofile=~/.vim/viminfo

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => General settings
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

set backspace=indent,eol,start
set ruler
set magic
set so=7
set noerrorbells
set novisualbell
set t_vb=
set hid
set lazyredraw

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Look and feel
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

colorscheme zenburn
set background=dark
set hlsearch
set incsearch
set showmatch
set wildmenu
set number
set cmdheight=2
set t_ut=

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Text settings
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

set wrap
set lbr
set tw=0

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Codeish settings
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

syntax enable
set smartindent
set expandtab
set shiftwidth=2
set softtabstop=2
"set list
set listchars=eol:$,tab:>-,trail:~,extends:>,precedes:<

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Functions
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

function! CurDir()
  let curdir = substitute(getcwd(), $HOME, "~/", "g")
  return curdir
endfunction

function! PasteStatus()
  let s:inPaste = &paste
  if !s:inPaste
    return ""
  else
    return "[PASTE MODE]"
  endif
endfunction

function! PasteToggle()
  let s:inPaste = &paste
  if !s:inPaste
    set paste
  else
    set nopaste
  endif
endfunction

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Bindings
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

let mapleader = ","
let g:mapleader = ","

"quick edit vim file and reload when saving
map <leader>e :e! $MYVIMRC<cr>
augroup vimrc_group
  autocmd!
  autocmd bufwritepost $MYVIMRC nested source $MYVIMRC
augroup END

"bind space to search
map <space> /
map <c-space> ?
map <silent> <leader><cr> :noh<cr>

"This won't  work here since putty is shit
map <silent> <c-tab> :bnext<cr>
map <silent> <c-s-tab> :bprevious<cr>

"Even this wont work
map <silent> <c-right> <esc>:bn<cr>
map <silent> <c-left> <esc>:bp<cr>

"using this instead
map <silent> <leader>bn :bn<cr>
map <silent> <leader>bp :bp<cr>
map <silent> <leader>bl :set nomore <bar> :ls <bar> :set more<cr>

"Switch CWD to focused files folder
map <silent> <leader>cd :cd %:p:h<cr>

"toggle spell checking
map <leader>ss :setlocal spell!<cr>

"Don't judge me!! The pastetoggle binding does not update the statusline
map <silent> <leader>p :call PasteToggle()<cr>
"set pastetoggle=<leader>p

"Rightfully stolen!
map <silent> <leader>q :set list! <cr>

nnoremap <leader>gd :YcmCompleter GoToDefinition<CR>
nnoremap <leader>gr :YcmCompleter GoToReferences<CR>
"nnoremap <leader>d :tab split \| YcmCompleter GoToDefinition<CR>

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Syntax highlighting
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

hi gitConflicts ctermfg=red
augroup git_conflict_vimrc_group
  autocmd!
  au filetype * syn match gitConflicts "^\(<<<<<<<\|=======\|>>>>>>>\)"
  au BufEnter,BufLeave * syn match gitConflicts "^\(<<<<<<<\|=======\|>>>>>>>\)"
augroup END

highlight ExtraWhitespace ctermbg=red guibg=red
augroup hi_whitspaces_vimrc_group
  autocmd!
  autocmd Syntax * syn match ExtraWhitespace /\s\+$\| \+\ze\t/
augroup END

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Statusline
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

hi LineInfoColor ctermbg=234 ctermfg=2
hi PasteStatusColor ctermbg=234 ctermfg=1
hi BufferColor ctermbg=234 ctermfg=5
hi FilenameColor ctermbg=234 ctermfg=12
hi CWDColor ctermbg=234 ctermfg=3

set laststatus=2
set statusline=%#BufferColor#
set statusline+=\ [%n]
set statusline+=%#FilenameColor#
set statusline+=\ %F%m%r%h\ %w
set statusline+=%#CWDColor#
set statusline+=\ CWD:\ %{CurDir()}
set statusline+=\ %=
set statusline+=%#PasteStatusColor#\ %{PasteStatus()}
set statusline+=%#LineInfoColor#\ Line:\ %l/%L:%c\ "This line skrews with my syntaxhighlighting
set statusline+=%#warningmsg#
set statusline+=%{SyntasticStatuslineFlag()}
set statusline+=%*

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Addon settings
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

" make YCM compatible with UltiSnips (using supertab)
let g:ycm_key_list_select_completion = ['<C-n>', '<Down>']
let g:ycm_key_list_previous_completion = ['<C-p>', '<Up>']
let g:SuperTabDefaultCompletionType = '<C-n>'

" better key bindings for UltiSnipsExpandTrigger
let g:UltiSnipsExpandTrigger = "<tab>"
let g:UltiSnipsJumpForwardTrigger = "<tab>"
let g:UltiSnipsJumpBackwardTrigger = "<s-tab>"

let g:ycm_enable_semantic_highlighting=1

let g:cpp_class_scope_highlight = 1
let g:cpp_experimental_template_highlight = 1

let g:syntastic_always_populate_loc_list = 1
let g:syntastic_auto_loc_list = 1
let g:syntastic_check_on_open = 1
let g:syntastic_check_on_wq = 0
let g:syntastic_python_flake8_args = "--max-line-length 256"
let g:syntastic_python_checkers = ['mypy', 'flake8']

let g:ctrlp_map = '<c-p>'
let g:ctrlp_cmd = 'CtrlPMixed'


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Fix for st
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

if &term =~ '256color'
    set t_ut=
endif

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" => Better place for this
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

"filetype plugin indent on


