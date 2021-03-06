## general imports
import os, sys, json, datetime, jinja2
from jinja2 import Template

## COCO imports
from pycocotools.coco import COCO
from pycocotools.cocoanalyze import COCOanalyze

## Analysis API imports
from analysisAPI.errorsAPImpact import errorsAPImpact
from analysisAPI.localizationErrors import localizationErrors
from analysisAPI.scoringErrors import scoringErrors
from analysisAPI.backgroundFalsePosErrors import backgroundFalsePosErrors
from analysisAPI.backgroundFalseNegErrors import backgroundFalseNegErrors
from analysisAPI.occlusionAndCrowdingSensitivity import occlusionAndCrowdingSensitivity
from analysisAPI.sizeSensitivity import sizeSensitivity

import numpy as np # i. 내가임포트함.

def main():

    # i. 넘파이 연산 에러 디버그하기위해 여기에 numpy.seterr(...) 넣어줘봄. ->잘 작동하는듯.
    # np.seterr(all='raise')
    # np.seterr(all='warn', divide='raise')
    # i. all, divide, over, under, invalid 각각에 대해 {‘ignore’, ‘warn’, ‘raise’, ‘call’, ‘print’, ‘log’} 의 옵션이 있음.
    np_seterr_setting_j = {'divide': 'raise', 'over': 'warn', 'under': 'warn', 'invalid': 'raise'} 
    np.seterr(**np_seterr_setting_j)

    print('j) sys.argv:',sys.argv)
    print('j) len(sys.argv):',len(sys.argv))    
    # i. 이 파일(run_analysis.py)실행할때 커맨드라인 아규먼트로 맨마지막에 OKS sigmas 도 추가하도록 내가 수정함.
    # i. 바로아랫부분도 바꺼줌. 아규먼트 하나 더 추가했으니.
    if len(sys.argv) != 7:
        raise ValueError("Please specify args: $> python run_analysis.py [annotations_path] [detections_path] [save_dir] [team_name] [version_name] [oks_sigmas_str_j]")

    latex_jinja_env = jinja2.Environment(
        block_start_string    = '\BLOCK{',
        block_end_string      = '}',
        variable_start_string = '\VAR{',
        variable_end_string   = '}',
        comment_start_string  = '\#{',
        comment_end_string    = '}',
        line_statement_prefix = '%%',
        line_comment_prefix   = '%#',
        trim_blocks           = True,
        autoescape            = False,
        loader                = jinja2.FileSystemLoader(os.path.abspath('./latex/'))
    )
    template = latex_jinja_env.get_template('report_template.tex') # i. 걍 이렇게하는게맞는듯한데... 위에서 ./latex/ 라고 해줫으니..
    template_vars  = {}

    annFile   = sys.argv[1]; splitName = annFile.split("/")[-1]
    resFile  = sys.argv[2]
    print("{:10}[{}]\n{:10}[{}]".format('annFile:',annFile,'resFile:',resFile))
    saveDir  = sys.argv[3]
    if not os.path.exists(saveDir):
        os.makedirs(saveDir)
    teamName    = sys.argv[4]
    versionName = sys.argv[5]
    oks_sigmas_str_j = sys.argv[6] # i. 내가추가한부분.
    oks_sigmas_j = list(map(float, oks_sigmas_str_j.strip('[]').split(',')))
    print('j) (run_analysis.py main()) oks_sigmas_j:{}, its type:{}'.format(oks_sigmas_j, type(oks_sigmas_j)))

    ## create dictionary with all images info
    gt_data   = json.load(open(annFile,'r'))
    imgs_info = {i['id']:{'id'      :i['id'] ,
                          'width'   :i['width'],
                          'height'  :i['height'],
                        # 'coco_url':i['coco_url']}  # i. KeyError: 'coco_url' 에러떠서 일단코멘트아웃. 아마 gt어노json에 coco_url정보 없엇던듯.지금밖이라이따집가서확인할예정.->ㅇㅇ맞음.
                 
                          # i. coco_url 은 없으니, key는 그대로 'coco_url' 로 하되, value를 이미지파일의 경로로 해줘봄(요 coco_url키가 몇군데에서 쓰여서 걍 살려주는게나을듯.).
                          'coco_url': '/content/pa_keypointj_upper_val/{}'.format(i['file_name'])}

                 for i in gt_data['images']}

    ## load team detections
    dt_data  = json.load(open(resFile,'r')) # i. 내생각이맞다면, dt_data는 COCO형식의 어노테이션json의 "annotations"키의 밸류임. 즉, [{어노1정보},{어노2정보},...] 이런 리스트.
    team_dts = {}
    for d in dt_data: # i. image id 별로 묶어줌. image id 가 키이고, 밸류는 [{해당이미지의 어노1정보}, {해당이미지의 어노2정보},...] 이런식.
        if d['image_id'] in team_dts: team_dts[d['image_id']].append(d)
        else: team_dts[d['image_id']] = [d]
    team_split_dts = []
    # i. 각 image id 별로, score 상위 20개 어노테이션정보(dict)들만 score높은순서대로 정렬해서 텅빈리스트에 extend해줌.
    # 즉, 결과물은 [{이미지1의 어노3정보}, {이미지1의 어노8정보},... {이미지2의 어노5정보}, {이미지2의 어노12정보}, ...] 이런식이 되겠지.
    # (이미지1에서 어노3,어노8,...순서로 점수1등,2등,...이고 이미지2에서 어노5,어노12,...순서로 점수1등,2등,... 이라고 치면말야.)
    for img_id in team_dts: 
        if img_id in imgs_info:
            team_split_dts.extend(sorted(team_dts[img_id], key=lambda k: -k['score'])[:20])
    print("Loaded [{}] detections from [{}] images.".format(len(team_split_dts),len(imgs_info)))
    template_vars['team_name']    = teamName
    template_vars['version_name'] = versionName
    template_vars['split_name']   = splitName
    template_vars['num_dts']      = len(team_split_dts)
    template_vars['num_imgs_dts'] = len(set([d['image_id'] for d in team_split_dts]))
    template_vars['num_imgs']     = len(imgs_info)

    ## load ground truth annotations
    coco_gt = COCO( annFile )

    ## initialize COCO detections api
    coco_dt   = coco_gt.loadRes( team_split_dts ) # i. COCOanalyze_demo.ipynb 에서는 team_split_dts 말고 resFile을 json.load한걸 그대로 넣어줬었는데, 여기선 각 이미지마다 상위20개어노만뽑아서 점수순으로 정렬한걸 넣어주네.

    ## initialize COCO analyze api
    # coco_analyze = COCOanalyze(coco_gt, coco_dt, 'keypoints')
    coco_analyze = COCOanalyze(coco_gt, coco_dt, oks_sigmas_j,'keypoints') # i. COCOanalyze 클래스를 내가수정해줬으므로 그에맞게 인풋인자 넣어줌(oks_sigmas_j 가 내가추가해준거.).
    if teamName == 'fakekeypoints100':
        imgIds  = sorted(coco_gt.getImgIds())[0:100]
        coco_analyze.cocoEval.params.imgIds = imgIds

    ## regular evaluation
    coco_analyze.evaluate(verbose=True, makeplots=True, savedir=saveDir, team_name=teamName)
    template_vars['overall_prc_medium'] = '%s/prc_[%s][medium][%d].pdf'%(saveDir,teamName,coco_analyze.params.maxDets[0])
    template_vars['overall_prc_large']  = '%s/prc_[%s][large][%d].pdf'%(saveDir,teamName,coco_analyze.params.maxDets[0])
    template_vars['overall_prc_all']    = '%s/prc_[%s][all][%d].pdf'%(saveDir,teamName,coco_analyze.params.maxDets[0])

    ############################################################################
    # COMMENT OUT ANY OF THE BELOW TO SKIP FROM ANALYSIS

    ## analyze imapct on AP of all error types
    paths = errorsAPImpact( coco_analyze, saveDir )
    template_vars.update(paths)

    ## analyze breakdown of localization errors
    paths = localizationErrors( coco_analyze, imgs_info, saveDir )
    template_vars.update(paths)

    ## analyze scoring errors
    paths = scoringErrors( coco_analyze, .75, imgs_info, saveDir )
    template_vars.update(paths)

    ## analyze background false positives
    paths = backgroundFalsePosErrors( coco_analyze, imgs_info, saveDir )
    template_vars.update(paths)

    ## analyze background false negatives
    paths = backgroundFalseNegErrors( coco_analyze, imgs_info, saveDir )
    template_vars.update(paths)

    ## analyze sensitivity to occlusion and crowding of instances
    paths = occlusionAndCrowdingSensitivity( coco_analyze, .75, saveDir )
    template_vars.update(paths)

    ## analyze sensitivity to size of instances
    paths = sizeSensitivity( coco_analyze, .75, saveDir )
    template_vars.update(paths)

    output_report = open('./%s_performance_report.tex'%teamName, 'w')
    output_report.write( template.render(template_vars) )
    output_report.close()

if __name__ == '__main__':
    main()
